# This is improved version with no error of slope (i.e, non-monotonic issues in FEA)
# User inputs
amplitudes_mm = [2, 4.5, 6.75, 9, 18, 27, 36, 49.5, 63, 90, 117, 144]
cycles_per_level = 3
time_scale_factor = 20.0
excel_filename = "cyclic_loading_protocol.xlsx"

# Required libraries
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# font setup
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'serif']
plt.rcParams['font.size'] = 11


# Displacement history
time = []
displacement = []

t = 0.0
dt = time_scale_factor

time.append(t)
displacement.append(0.0)
t += dt

for amp in amplitudes_mm:
    for _ in range(cycles_per_level):
        # +amp
        time.append(t)
        displacement.append(amp)
        t += dt

        # -amp
        time.append(t)
        displacement.append(-amp)
        t += dt

time.append(t)
displacement.append(0.0)

time = np.array(time)
displacement = np.array(displacement)


# Save to Excel

df = pd.DataFrame({
    'Time (s)': time,
    'Displacement (mm)': displacement
})

df.to_excel(excel_filename, index=False)
print(f"Saved: {excel_filename}")
print(f"Rows (true protocol points): {len(df)}")

# Plot

fig, ax = plt.subplots(figsize=(14, 7))
ax.plot(time, displacement, lw=1.5)

# Labels on plots
for x, y in zip(time, displacement):
    if x == 0 and y == 0:
        ax.text(x, y, "(0, 0)", ha='right', va='top', fontsize=10)
    elif y != 0:
        va = 'bottom' if y > 0 else 'top'
        offset = 2.0 if y > 0 else -2.0
        ax.text(x, y + offset, f"{y:g}",
                ha='center', va=va, fontsize=8)

ax.set_title("Peak-Based Cyclic Loading Protocol")
ax.set_xlabel("Time [s]")
ax.set_ylabel("Displacement [mm]")
ax.grid(True, linestyle=':', alpha=0.4)

plt.tight_layout()
plt.show()

print(f"Total duration: {time[-1]} s")
print(f"Max amplitude: ±{amplitudes_mm[-1]} mm")
