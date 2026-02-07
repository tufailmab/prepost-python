import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Load Excel file
df = pd.read_excel("FD Curve.xlsx", header=0)
displacement = df.iloc[:, 0].values
force = df.iloc[:, 1].values

# -------------------------
# Tangent Stiffness (Point-to-Point)
# -------------------------
delta_F = np.diff(force)
delta_d = np.diff(displacement)
tangent_stiffness = delta_F / delta_d
# Midpoint displacement for plotting
displacement_mid = (displacement[:-1] + displacement[1:]) / 2

# -------------------------
# Secant Stiffness (w.r.t Origin)
# -------------------------
# Avoid division by zero at origin
nonzero_indices = displacement != 0
displacement_nonzero = displacement[nonzero_indices]
force_nonzero = force[nonzero_indices]
secant_stiffness = force_nonzero / displacement_nonzero

# -------------------------
# Create output folder
# -------------------------
output_folder = "Required Outputs"
os.makedirs(output_folder, exist_ok=True)

# Save tangent stiffness data
tangent_df = pd.DataFrame({
    "Displacement_mm": displacement_mid,
    "Tangent_Stiffness_kN_per_mm": tangent_stiffness
})
tangent_file = os.path.join(output_folder, "Tangent_Stiffness.txt")
tangent_df.to_csv(tangent_file, index=False, sep='\t')

# Save secant stiffness data
secant_df = pd.DataFrame({
    "Displacement_mm": displacement_nonzero,
    "Secant_Stiffness_kN_per_mm": secant_stiffness
})
secant_file = os.path.join(output_folder, "Secant_Stiffness.txt")
secant_df.to_csv(secant_file, index=False, sep='\t')

# -------------------------
# Plotting
# -------------------------
plt.rcParams["font.family"] = "Times New Roman"

# Tangent stiffness plot
plt.figure(figsize=(8,5))
plt.plot(displacement_mid, tangent_stiffness, marker='o', linestyle='-', color='b', label='Tangent Stiffness')
plt.xlabel("Displacement (mm)", fontsize=12)
plt.ylabel("Stiffness (kN/mm)", fontsize=12)
plt.legend(fontsize=10)
plt.grid(False)
plt.savefig(os.path.join(output_folder, "Tangent_Stiffness.png"), dpi=300, bbox_inches='tight')
plt.show()

# Secant stiffness plot
plt.figure(figsize=(8,5))
plt.plot(displacement_nonzero, secant_stiffness, marker='o', linestyle='-', color='r', label='Secant Stiffness')
plt.xlabel("Displacement (mm)", fontsize=12)
plt.ylabel("Stiffness (kN/mm)", fontsize=12)
plt.legend(fontsize=10)
plt.grid(False)
plt.savefig(os.path.join(output_folder, "Secant_Stiffness.png"), dpi=300, bbox_inches='tight')
plt.show()

print(f"All outputs saved in folder: '{output_folder}'")
