# Import all required libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Load Excel file
df = pd.read_excel("FD Curve.xlsx", header=0)
displacement = df.iloc[:, 0].values
force = df.iloc[:, 1].values

# Energy Absorbed Calculation
# Cumulative trapezoidal integration
energy_absorbed = np.zeros_like(force)  # initialize array
for i in range(1, len(force)):
    energy_absorbed[i] = energy_absorbed[i-1] + 0.5*(force[i] + force[i-1])*(displacement[i] - displacement[i-1])

# Create output folder
output_folder = "Required Outputs"
os.makedirs(output_folder, exist_ok=True)

# Save energy absorbed data
energy_df = pd.DataFrame({
    "Displacement (mm)": displacement,
    "Energy Absorbed (kN.mm)": energy_absorbed
})
energy_file = os.path.join(output_folder, "Energy_Absorbed.txt")
energy_df.to_csv(energy_file, index=False, sep='\t')

# Plotting Energy vs Displacement
plt.rcParams["font.family"] = "Times New Roman"
plt.figure(figsize=(8,5))
plt.plot(displacement, energy_absorbed, marker='o', linestyle='-', color='g', label='Energy Absorbed')
plt.xlabel("Displacement (mm)", fontsize=12)
plt.ylabel("Energy Absorbed (kN·mm)", fontsize=12)
plt.legend(fontsize=10)
plt.grid(False)

# Save the plot
plot_file = os.path.join(output_folder, "Energy_Absorbed.png")
plt.savefig(plot_file, dpi=300, bbox_inches='tight')
plt.show()

print(f"Energy absorbed data and plot saved in folder: '{output_folder}'")

