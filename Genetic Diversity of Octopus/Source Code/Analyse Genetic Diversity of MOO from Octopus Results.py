# Import All Required Libraries
import os
import numpy as np
import pandas as pd

# File name (change if needed)
file_name = "Generation No.txt"  # put your txt file name here

# Read and clean data
with open(file_name, 'r') as f:
    lines = f.readlines()

# Remove first line and strip spaces
clean_lines = [
    line.strip()
    for line in lines
    if line.strip() != "" and "Generation" not in line
]

# Convert to float
values = [float(x) for x in clean_lines]

# Group every 4 values into one row
data = [values[i:i+4] for i in range(0, len(values), 4)]

# Create DataFrame
df = pd.DataFrame(data, columns=["F1", "F2", "F3", "GD"])

# Compute statistics
stats = pd.DataFrame({
    "Min": df.min(),
    "Max": df.max(),
    "Mean": df.mean()
})

# Display results
print("\nStatistical Summary of Final Pareto Generation:\n")
print(stats.round(4))

# Optional: save to Excel for paper
stats.to_excel("Pareto Statistics.xlsx")
df.to_excel("Pareto Full data.xlsx", index=False)

print("\nFiles saved:")
print(" - Pareto Statistics.xlsx (for table in paper)")
print(" - Pareto Full data.xlsx (all solutions)")
