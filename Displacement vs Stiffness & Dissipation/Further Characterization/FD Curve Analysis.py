import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# -------------------------
# Load FD curve
# -------------------------
file_name = "FD Curve.xlsx"
df = pd.read_excel(file_name, header=0)
displacement = df.iloc[:, 0].values
force = df.iloc[:, 1].values

# Avoid division by zero for secant stiffness
nonzero_idx = displacement != 0
displacement_nonzero = displacement[nonzero_idx]
force_nonzero = force[nonzero_idx]

# -------------------------
# Create output folder
# -------------------------
output_folder = "Required Outputs"
os.makedirs(output_folder, exist_ok=True)

plt.rcParams["font.family"] = "Times New Roman"

# -------------------------
# Task 1: Raw FD Curve
# -------------------------
plt.figure(figsize=(8,5))
plt.plot(displacement, force, marker='o', linestyle='-', color='k', label='FD Curve')
plt.xlabel("Displacement (mm)", fontsize=12)
plt.ylabel("Force (kN)", fontsize=12)
plt.legend(fontsize=10)
plt.grid(False)
plt.savefig(os.path.join(output_folder, "FD_Curve.png"), dpi=300, bbox_inches='tight')
plt.close()

# -------------------------
# Task 2: Tangent stiffness
# -------------------------
delta_F = np.diff(force)
delta_d = np.diff(displacement)
tangent_stiffness = delta_F / delta_d
displacement_mid = (displacement[:-1] + displacement[1:])/2

tangent_df = pd.DataFrame({"Displacement_mm": displacement_mid,
                           "Tangent_Stiffness_kN_per_mm": tangent_stiffness})
tangent_df.to_csv(os.path.join(output_folder, "Tangent_Stiffness.txt"), index=False, sep='\t')

plt.figure(figsize=(8,5))
plt.plot(displacement_mid, tangent_stiffness, marker='o', linestyle='-', color='b', label='Tangent Stiffness')
plt.xlabel("Displacement (mm)", fontsize=12)
plt.ylabel("Stiffness (kN/mm)", fontsize=12)
plt.legend(fontsize=10)
plt.grid(False)
plt.savefig(os.path.join(output_folder, "Tangent_Stiffness.png"), dpi=300, bbox_inches='tight')
plt.close()

# -------------------------
# Task 3: Secant stiffness
# -------------------------
secant_stiffness = force_nonzero / displacement_nonzero

secant_df = pd.DataFrame({"Displacement_mm": displacement_nonzero,
                          "Secant_Stiffness_kN_per_mm": secant_stiffness})
secant_df.to_csv(os.path.join(output_folder, "Secant_Stiffness.txt"), index=False, sep='\t')

plt.figure(figsize=(8,5))
plt.plot(displacement_nonzero, secant_stiffness, marker='o', linestyle='-', color='r', label='Secant Stiffness')
plt.xlabel("Displacement (mm)", fontsize=12)
plt.ylabel("Stiffness (kN/mm)", fontsize=12)
plt.legend(fontsize=10)
plt.grid(False)
plt.savefig(os.path.join(output_folder, "Secant_Stiffness.png"), dpi=300, bbox_inches='tight')
plt.close()

# -------------------------
# Task 4: Energy absorbed
# -------------------------
energy_absorbed = np.zeros_like(force)
for i in range(1,len(force)):
    energy_absorbed[i] = energy_absorbed[i-1] + 0.5*(force[i]+force[i-1])*(displacement[i]-displacement[i-1])

energy_df = pd.DataFrame({"Displacement_mm": displacement,
                          "Energy_Absorbed_kN_mm": energy_absorbed})
energy_df.to_csv(os.path.join(output_folder, "Energy_Absorbed.txt"), index=False, sep='\t')

plt.figure(figsize=(8,5))
plt.plot(displacement, energy_absorbed, marker='o', linestyle='-', color='g', label='Energy Absorbed')
plt.xlabel("Displacement (mm)", fontsize=12)
plt.ylabel("Energy Absorbed (kN·mm)", fontsize=12)
plt.legend(fontsize=10)
plt.grid(False)
plt.savefig(os.path.join(output_folder, "Energy_Absorbed.png"), dpi=300, bbox_inches='tight')
plt.close()

# -------------------------
# Task 5: Max force & displacement
# -------------------------
max_force_idx = np.argmax(force)
max_force = force[max_force_idx]
max_displacement = displacement[max_force_idx]

plt.figure(figsize=(8,5))
plt.plot(displacement, force, marker='o', linestyle='-', color='k', label='FD Curve')
plt.scatter(max_displacement, max_force, color='r', s=80, label='Max Force Point')
plt.xlabel("Displacement (mm)", fontsize=12)
plt.ylabel("Force (kN)", fontsize=12)
plt.legend(fontsize=10)
plt.grid(False)
plt.savefig(os.path.join(output_folder, "FD_Curve_MaxPoint.png"), dpi=300, bbox_inches='tight')
plt.close()

# -------------------------
# Task 6: Normalized force
# -------------------------
normalized_force = force / max_force
plt.figure(figsize=(8,5))
plt.plot(displacement, normalized_force, marker='o', linestyle='-', color='m', label='Normalized Force')
plt.xlabel("Displacement (mm)", fontsize=12)
plt.ylabel("F / F_max", fontsize=12)
plt.legend(fontsize=10)
plt.grid(False)
plt.savefig(os.path.join(output_folder, "Normalized_Force.png"), dpi=300, bbox_inches='tight')
plt.close()

# -------------------------
# Task 7: Normalized displacement
# -------------------------
normalized_displacement = displacement / max_displacement
plt.figure(figsize=(8,5))
plt.plot(normalized_displacement, force, marker='o', linestyle='-', color='c', label='Normalized Displacement')
plt.xlabel("d / d_max", fontsize=12)
plt.ylabel("Force (kN)", fontsize=12)
plt.legend(fontsize=10)
plt.grid(False)
plt.savefig(os.path.join(output_folder, "Normalized_Displacement.png"), dpi=300, bbox_inches='tight')
plt.close()

# -------------------------
# Task 8: Tangent vs Secant Stiffness
# -------------------------
plt.figure(figsize=(8,5))
plt.plot(displacement_mid, tangent_stiffness, marker='o', linestyle='-', color='b', label='Tangent Stiffness')
plt.plot(displacement_nonzero, secant_stiffness, marker='o', linestyle='--', color='r', label='Secant Stiffness')
plt.xlabel("Displacement (mm)", fontsize=12)
plt.ylabel("Stiffness (kN/mm)", fontsize=12)
plt.legend(fontsize=10)
plt.grid(False)
plt.savefig(os.path.join(output_folder, "Tangent_vs_Secant.png"), dpi=300, bbox_inches='tight')
plt.close()

# -------------------------
# Task 9: Save all processed data into Excel
# -------------------------
with pd.ExcelWriter(os.path.join(output_folder, "FD_Curve_Analysis.xlsx")) as writer:
    df.to_excel(writer, sheet_name="Raw_FD", index=False)
    tangent_df.to_excel(writer, sheet_name="Tangent_Stiffness", index=False)
    secant_df.to_excel(writer, sheet_name="Secant_Stiffness", index=False)
    energy_df.to_excel(writer, sheet_name="Energy_Absorbed", index=False)

print(f"All outputs saved in folder: '{output_folder}'")
