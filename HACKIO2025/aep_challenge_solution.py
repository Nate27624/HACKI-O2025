#!/usr/bin/env python3

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pypsa
import sys
import warnings
warnings.filterwarnings('ignore')

# Add IEEE 738 module
sys.path.append('ieee738')
from ieee738.ieee738 import ConductorParams
import ieee738.ieee738 as ieee738

class AEPGridChallenge:
    def __init__(self):
        self.load_data()
        self.setup_ieee738_defaults()
        
    def load_data(self):
        """Load all grid data"""
        self.lines_df = pd.read_csv('hawaii40_osu/csv/lines.csv')
        self.flows_df = pd.read_csv('hawaii40_osu/line_flows_nominal.csv')
        self.conductor_df = pd.read_csv('ieee738/conductor_library.csv')
        self.buses_df = pd.read_csv('hawaii40_osu/csv/buses.csv')
        
        # Merge data
        self.grid_data = self.lines_df.merge(self.flows_df, on='name')
        self.grid_data = self.grid_data.merge(self.conductor_df, left_on='conductor', right_on='ConductorName')
        self.grid_data = self.grid_data.merge(self.buses_df[['name', 'v_nom']], left_on='bus0', right_on='name', suffixes=('', '_bus'))
        
    def setup_ieee738_defaults(self):
        """Setup IEEE 738 ambient defaults"""
        self.ambient_defaults = {
            'WindVelocity': 2.0,
            'WindAngleDeg': 90,
            'SunTime': 12,
            'Date': '12 Jun',
            'Emissivity': 0.8,
            'Absorptivity': 0.8,
            'Direction': 'EastWest',
            'Atmosphere': 'Clear',
            'Elevation': 1000,
            'Latitude': 27,
        }
    
    def calculate_dynamic_rating(self, conductor_name, mot, ambient_temp, wind_speed):
        """Calculate IEEE 738 dynamic rating"""
        conductor_row = self.conductor_df[self.conductor_df['ConductorName'] == conductor_name].iloc[0]
        
        conductor_params = {
            'Ta': ambient_temp,
            'WindVelocity': wind_speed,
            'TLo': 25,
            'THi': 50,
            'RLo': conductor_row['RES_25C'] / 5280,
            'RHi': conductor_row['RES_50C'] / 5280,
            'Diameter': conductor_row['CDRAD_in'] * 2,
            'Tc': mot,
        }
        
        all_params = {**self.ambient_defaults, **conductor_params}
        
        try:
            cp = ConductorParams(**all_params)
            conductor = ieee738.Conductor(cp)
            return conductor.steady_state_thermal_rating()
        except:
            return None
    
    def analyze_temperature_impact(self, temp_range=(25, 60), wind_speed=2.0):
        """CHALLENGE 1: At what temperature do lines start overloading?"""
        temperatures = range(temp_range[0], temp_range[1] + 1, 5)
        results = []
        
        for temp in temperatures:
            overloaded_count = 0
            max_loading = 0
            
            for _, line in self.grid_data.iterrows():
                rating_amps = self.calculate_dynamic_rating(line['conductor'], line['MOT'], temp, wind_speed)
                if rating_amps:
                    rating_mva = np.sqrt(3) * rating_amps * line['v_nom'] * 1000 / 1e6
                    loading_pct = (line['p0_nominal'] / rating_mva) * 100
                    
                    if loading_pct > 100:
                        overloaded_count += 1
                    max_loading = max(max_loading, loading_pct)
            
            results.append({
                'temperature': temp,
                'overloaded_lines': overloaded_count,
                'max_loading': max_loading
            })
        
        return pd.DataFrame(results)
    
    def find_critical_temperature(self, wind_speed=2.0):
        """Find first overload temperature"""
        for temp in range(25, 70):
            for _, line in self.grid_data.iterrows():
                rating_amps = self.calculate_dynamic_rating(line['conductor'], line['MOT'], temp, wind_speed)
                if rating_amps:
                    rating_mva = np.sqrt(3) * rating_amps * line['v_nom'] * 1000 / 1e6
                    loading_pct = (line['p0_nominal'] / rating_mva) * 100
                    if loading_pct > 100:
                        return temp
        return None
    
    def identify_critical_lines(self, ambient_temp=50, wind_speed=2.0):
        """CHALLENGE 2: Which lines overload first?"""
        critical_lines = []
        
        for _, line in self.grid_data.iterrows():
            rating_amps = self.calculate_dynamic_rating(line['conductor'], line['MOT'], ambient_temp, wind_speed)
            if rating_amps:
                rating_mva = np.sqrt(3) * rating_amps * line['v_nom'] * 1000 / 1e6
                loading_pct = (line['p0_nominal'] / rating_mva) * 100
                
                critical_lines.append({
                    'name': line['name'],
                    'branch_name': line['branch_name'],
                    'conductor': line['conductor'],
                    'loading_pct': loading_pct,
                    'overloaded': loading_pct > 100
                })
        
        df = pd.DataFrame(critical_lines)
        return df.sort_values('loading_pct', ascending=False)
    
    def assess_system_stress(self, ambient_temp, wind_speed=2.0):
        """CHALLENGE 3: System stress categorization"""
        loadings = []
        
        for _, line in self.grid_data.iterrows():
            rating_amps = self.calculate_dynamic_rating(line['conductor'], line['MOT'], ambient_temp, wind_speed)
            if rating_amps:
                rating_mva = np.sqrt(3) * rating_amps * line['v_nom'] * 1000 / 1e6
                loading_pct = (line['p0_nominal'] / rating_mva) * 100
                loadings.append(loading_pct)
        
        loadings = np.array(loadings)
        
        critical = len(loadings[loadings >= 90])
        caution = len(loadings[(loadings >= 60) & (loadings < 90)])
        normal = len(loadings[loadings < 60])
        
        return {
            'temperature': ambient_temp,
            'critical_lines': critical,
            'caution_lines': caution,
            'normal_lines': normal,
            'max_loading': loadings.max(),
            'avg_loading': loadings.mean()
        }
    
    def run_n1_contingency(self, ambient_temp=35, wind_speed=2.0):
        """BONUS: N-1 Contingency Analysis"""
        # Load PyPSA network
        network = pypsa.Network()
        network.import_from_csv_folder('hawaii40_osu/csv')
        network.pf()
        
        violations = []
        
        for line_out in network.lines.index[:10]:  # Test first 10 lines
            # Create contingency network
            cont_network = network.copy()
            cont_network.lines.drop(line_out, inplace=True)
            
            try:
                cont_network.pf()
                
                # Check post-contingency loadings
                flows = cont_network.lines_t.p0.iloc[0]
                
                for line_name, flow in flows.items():
                    if line_name in self.grid_data['name'].values:
                        line_data = self.grid_data[self.grid_data['name'] == line_name].iloc[0]
                        rating_amps = self.calculate_dynamic_rating(line_data['conductor'], line_data['MOT'], ambient_temp, wind_speed)
                        
                        if rating_amps:
                            rating_mva = np.sqrt(3) * rating_amps * line_data['v_nom'] * 1000 / 1e6
                            loading_pct = (abs(flow) / rating_mva) * 100
                            
                            if loading_pct > 80:
                                violations.append({
                                    'contingency': line_out,
                                    'overloaded_line': line_name,
                                    'loading_pct': loading_pct
                                })
            except:
                continue
        
        return violations
    
    def create_visualizations(self):
        """Create comprehensive visualizations"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. Temperature sensitivity
        temp_results = self.analyze_temperature_impact()
        ax1.plot(temp_results['temperature'], temp_results['max_loading'], 'ro-', linewidth=2)
        ax1.axhline(y=100, color='red', linestyle='--', label='100% Rating')
        ax1.set_xlabel('Temperature (°C)')
        ax1.set_ylabel('Max Loading (%)')
        ax1.set_title('System Stress vs Temperature')
        ax1.legend()
        ax1.grid(True)
        
        # 2. Critical lines at 50°C
        critical_lines = self.identify_critical_lines(50)
        top_10 = critical_lines.head(10)
        colors = ['red' if x > 100 else 'orange' if x > 90 else 'yellow' for x in top_10['loading_pct']]
        ax2.barh(range(len(top_10)), top_10['loading_pct'], color=colors)
        ax2.set_yticks(range(len(top_10)))
        ax2.set_yticklabels([name[:20] for name in top_10['name']], fontsize=8)
        ax2.set_xlabel('Loading (%)')
        ax2.set_title('Top 10 Critical Lines at 50°C')
        ax2.axvline(x=100, color='red', linestyle='--')
        
        # 3. System stress levels
        stress_temps = [30, 40, 50, 60]
        stress_data = [self.assess_system_stress(t) for t in stress_temps]
        
        critical_counts = [s['critical_lines'] for s in stress_data]
        caution_counts = [s['caution_lines'] for s in stress_data]
        normal_counts = [s['normal_lines'] for s in stress_data]
        
        ax3.bar(stress_temps, normal_counts, label='Normal (0-60%)', color='green', alpha=0.7)
        ax3.bar(stress_temps, caution_counts, bottom=normal_counts, label='Caution (60-90%)', color='orange', alpha=0.7)
        ax3.bar(stress_temps, critical_counts, bottom=np.array(normal_counts)+np.array(caution_counts), label='Critical (90%+)', color='red', alpha=0.7)
        ax3.set_xlabel('Temperature (°C)')
        ax3.set_ylabel('Number of Lines')
        ax3.set_title('System Stress Categories')
        ax3.legend()
        
        # 4. Wind impact
        wind_speeds = [0.5, 1.0, 2.0, 3.0, 5.0]
        wind_loadings = []
        for wind in wind_speeds:
            stress = self.assess_system_stress(50, wind)
            wind_loadings.append(stress['max_loading'])
        
        ax4.plot(wind_speeds, wind_loadings, 'bo-', linewidth=2)
        ax4.axhline(y=100, color='red', linestyle='--', label='100% Rating')
        ax4.set_xlabel('Wind Speed (ft/sec)')
        ax4.set_ylabel('Max Loading (%)')
        ax4.set_title('Wind Speed Impact at 50°C')
        ax4.legend()
        ax4.grid(True)
        
        plt.tight_layout()
        plt.savefig('aep_challenge_results.png', dpi=150, bbox_inches='tight')
        plt.show()

def main():
    """Main execution"""
    challenge = AEPGridChallenge()
    
    # CHALLENGE 1: Critical temperature
    critical_temp = challenge.find_critical_temperature()
    print(f"First overload occurs at: {critical_temp}°C")
    
    # CHALLENGE 2: Critical lines
    critical_lines = challenge.identify_critical_lines(50)
    print(f"\nMost critical lines at 50°C:")
    for _, line in critical_lines.head(5).iterrows():
        print(f"  {line['branch_name'][:50]}: {line['loading_pct']:.1f}%")
    
    # CHALLENGE 3: System stress assessment
    for temp in [30, 40, 50, 60]:
        stress = challenge.assess_system_stress(temp)
        status = "CRITICAL" if stress['critical_lines'] > 0 else "CAUTION" if stress['caution_lines'] > 5 else "NORMAL"
        print(f"\n{temp}°C: {stress['critical_lines']} critical, {stress['caution_lines']} caution - {status}")
    
    # BONUS: N-1 Analysis (sample)
    print(f"\nN-1 Contingency Analysis (sample):")
    violations = challenge.run_n1_contingency()
    for v in violations[:3]:
        print(f'For loss of "{v["contingency"]}"')
        print(f'  "{v["overloaded_line"]}" {v["loading_pct"]:.0f}%')
    
    # Create visualizations
    challenge.create_visualizations()

if __name__ == "__main__":
    main()