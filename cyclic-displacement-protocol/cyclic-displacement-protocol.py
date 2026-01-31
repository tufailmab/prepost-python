# This protocol is developed for a masonry wall cyclic loading analysis

#  All inputs required
#  Write Peaks of displacements (In array)
amplitudes_mm = [1, 2, 3, 4, 5, 8, 12, 15, 20, 25, 35, 50]

# full cycles per amplitude
cycles_per_level = 3

# points per ramp (0 → peak or peak → 0)
points_per_half  = 60

# seconds per half-cycle → adjust if needed
time_scale_factor = 20.0

excel_filename = "Dummy Protocol.xlsx"

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

#  Try to set Times New Roman (fallback to default if not found)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'serif']
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10

#  Displacement History

time = []
displacement = []
t = 0.0

peak_positions = []
peak_values = []

for amp in amplitudes_mm:
    for _ in range(cycles_per_level):
        # Positive half: 0 → +amp → 0
        t_half = np.linspace(0, 1, points_per_half)
        y_pos = np.where(t_half <= 0.5,
                         2 * amp * t_half,
                         2 * amp * (1 - t_half))

        time.extend(t + t_half)
        displacement.extend(y_pos)

        # Record positive peak (middle of half-cycle)
        peak_positions.append((t + 0.5) * time_scale_factor)
        peak_values.append(amp)

        t += 1.0

        # Negative half: 0 → -amp → 0
        y_neg = -y_pos
        time.extend(t + t_half)
        displacement.extend(y_neg)

        peak_positions.append((t + 0.5) * time_scale_factor)
        peak_values.append(-amp)

        t += 1.0

time = np.array(time) * time_scale_factor
displacement = np.array(displacement)

#  Save Results
df = pd.DataFrame({
    'Time (s)': time,
    'Displacement (mm)': displacement
})

df.to_excel(excel_filename, index=False,
            sheet_name='Cyclic Loading',
            float_format='%.6f')

print(f"Data saved to: {excel_filename}")
print(f"Rows saved: {len(df):,d}")

# Plot
fig, ax = plt.subplots(figsize=(14, 7))

ax.plot(time, displacement, 'b-', lw=1.3, label='Displacement')

# Zero lines
ax.axhline(0, color='k', lw=0.8, alpha=0.5, zorder=1)
ax.axvline(0, color='k', lw=0.8, alpha=0.5, zorder=1)

# Peak value labels
for px, py in zip(peak_positions, peak_values):
    va = 'bottom' if py > 0 else 'top'
    offset = 2.0 if py > 0 else -2.0
    
    ax.text(px, py + offset,
            f'{py:g} mm',
            ha='center', va=va,
            fontsize=7.8,
            color='darkblue',
            bbox=dict(facecolor='white', alpha=0.75, edgecolor='none', pad=1.3))

ax.set_title("Cyclic Loading Protocol – Triangular Waveform\n"
             f"{cycles_per_level} full cycles per level",
             pad=14)
ax.set_xlabel("Time [seconds]")
ax.set_ylabel("Displacement [mm]")

ax.grid(True, linestyle=':', alpha=0.35)
ax.legend(loc='upper left', framealpha=0.92)

ax.margins(x=0.005, y=0.08)
ax.set_xlim(left=0)

plt.tight_layout()
plt.show()

print(f"Total duration: {time[-1]:.0f} s  ({time[-1]/60:.1f} minutes)")
print(f"Max amplitude: ±{amplitudes_mm[-1]} mm")
