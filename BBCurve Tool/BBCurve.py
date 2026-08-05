"""
Backbone curve extractor + bilinear idealization for cyclic hysteresis data
Developed by: Tufail Mabood
GitHub: https://github.com/tufailmab
"""

# Required Input File Format:
# - Tab-delimited or whitespace-delimited .txt files
# - First row: header (skipped automatically)
# - Column 1: Displacement (mm)
# - Column 2: Force (kN)

# Usage:
# 1. Place all .txt files in the same folder as this script
# 2. Run: python BBCurve.py
# 3. Results saved in 'results/' folder with organized subfolders

# Assumptions (ASTM E2126):
# - STIFFNESS_FRACTION = 0.40 (secant through 40% of peak force)
# - DEGRADATION_FRACTION = 0.80 (ultimate = first drop to 80% of peak force)
# - EEEP method for bilinear idealization (Equal Energy Elastic-Plastic)

# Output Files:
# - Backbone curve (PNG plot + CSV)
# - Positive/Negative/Average branches (PNG plot + CSV)
# - Bilinear idealization (PNG plot + CSV)
# - Stiffness degradation (PNG plot + CSV)
# - Energy dissipation per cycle (PNG plot + CSV)
# - Cumulative energy dissipation (PNG plot + CSV)

# Disclaimer:
# This tool is for engineering analysis purposes only.
# Verify results against your specific testing standards.
# The developer assumes no liability for use of this script.

# A Note:
# I have kept j1.txt to j7.txt for running and testing, after completing libraries installing run it and it must work for you.

import os, glob, numpy as np, pandas as pd
import matplotlib.pyplot as plt
_trapezoid = getattr(np, "trapezoid", None) or np.trapz

STIFFNESS_FRACTION, DEGRADATION_FRACTION = 0.40, 0.80

# Folder structure - each specimen gets its own subfolder
FOLDERS = {
    "backbone_plots": "All Backbone Curves-Plots",
    "backbone_csv": "All Backbone Curves-CSVs",
    "pna_plots": "Positive-Negative-Average Plots",
    "pna_csv": "Positive-Negative-Average CSVs",
    "bilinear_plots": "Bilinear Idealization Plots",
    "bilinear_csv": "Bilinear Idealization CSVs",
    "stiffness_plots": "Stiffness Degradation Plots",
    "stiffness_csv": "Stiffness Degradation CSVs",
    "energy_plots": "Energy Dissipation Plots",
    "energy_csv": "Energy Dissipation CSVs",
    "summary": "Summary"
}

def load_data(path):
    df = pd.read_csv(path, header=0, names=["disp","force"], skiprows=1, delimiter='\t')
    if len(df.columns)!=2 or df.iloc[0].isnull().any():
        df = pd.read_csv(path, header=0, names=["disp","force"], skiprows=1, delim_whitespace=True)
    df = df[["disp","force"]].apply(pd.to_numeric, errors='coerce').dropna().reset_index(drop=True)
    if len(df)<3: raise ValueError("Not enough data")
    return df["disp"].to_numpy(), df["force"].to_numpy()

def reversal_points(disp, force):
    d = pd.Series(np.sign(np.where(np.diff(disp)==0, np.nan, np.diff(disp)))).ffill().bfill().to_numpy()
    turn = np.ones(len(disp), dtype=bool); turn[1:-1] = d[1:] != d[:-1]; turn[0]=turn[-1]=True
    return disp[turn], force[turn]

def envelope(x, y, tol=0.02):
    if len(x)==0: return np.array([]), np.array([])
    o = np.argsort(np.abs(x)); x, y = x[o], np.abs(y[o])
    tol *= np.max(np.abs(x))
    gx, gy = [], []
    cx, cy = [x[0]], [y[0]]
    for xi, yi in zip(x[1:], y[1:]):
        if xi - cx[-1] <= tol:
            cx.append(xi); cy.append(yi)
        else:
            gx.append(np.mean(cx)); gy.append(np.max(cy)); cx, cy = [xi], [yi]
    gx.append(np.mean(cx)); gy.append(np.max(cy))
    kx, ky = [], []
    mx = -np.inf
    for xi, yi in zip(gx, gy):
        if xi > mx: kx.append(xi); ky.append(yi); mx = xi
    return np.array(kx), np.array(ky)

def split_branches(disp, force):
    px, pf = reversal_points(disp, force)
    p_x, p_y = envelope(px[px>0], pf[px>0])
    n_x, n_y = envelope(-px[px<0], -pf[px<0])
    n_x, n_y = -n_x, -n_y
    return (np.concatenate([[0], p_x]), np.concatenate([[0], p_y]),
            np.concatenate([n_x[::-1], [0]]), np.concatenate([n_y[::-1], [0]]))

def backbone(disp, force):
    px, py, nx, ny = split_branches(disp, force)
    return np.concatenate([nx, px[1:]]), np.concatenate([ny, py[1:]]), px, py, nx, ny

def mirror(nx, ny): return -nx[::-1], -ny[::-1]

def average(px, py, mx, my):
    g = np.unique(np.concatenate([px, mx]))
    return g, (np.interp(g, px, py) + np.interp(g, mx, my)) / 2

def properties(x, y, sf=STIFFNESS_FRACTION, df=DEGRADATION_FRACTION):
    if len(x)<2 or np.max(y)<=0: return {"error":"No positive force"}
    i = np.argmax(y); Fmax, Dmax = y[i], x[i]
    Du, Fu = x[-1], y[-1]
    for j in range(i, len(x)-1):
        if y[j] >= df*Fmax and y[j+1] < df*Fmax:
            t = (df*Fmax - y[j])/(y[j+1]-y[j])
            Du, Fu = x[j] + t*(x[j+1]-x[j]), df*Fmax; break
    ax, ay = x[:i+1], y[:i+1]
    Ke = None
    for j in range(len(ax)-1):
        if ax[j] <= sf*Fmax <= ax[j+1] and ax[j+1]!=ax[j]:
            Dt = ax[j] + (sf*Fmax - ax[j])/(ax[j+1]-ax[j])*(ax[j+1]-ax[j])
            if Dt>0: Ke = sf*Fmax/Dt; break
    if Ke is None or not np.isfinite(Ke):
        Ke = (ay[1]-ay[0])/(ax[1]-ax[0]) if ax[1]!=ax[0] else np.nan
    mask = x <= Du
    cx, cy = list(x[mask]), list(y[mask])
    if len(cx)==0 or cx[-1]<Du: cx.append(Du); cy.append(Fu)
    Area = float(_trapezoid(cy, cx))
    Dy = Fy = duct = np.nan
    disc = (Ke*Du)**2 - 2*Ke*Area
    if Ke and np.isfinite(Ke) and Ke>0 and disc>=0:
        Fy = Ke*Du - np.sqrt(disc); Dy = Fy/Ke; duct = Du/Dy if Dy>0 else np.nan
    return {"Fmax_kN":Fmax,"Dmax_mm":Dmax,"Du_mm":Du,"Fu_kN":Fu,"Ke_kN_per_mm":Ke,
            "Energy_kN_mm":Area,"Dy_mm":Dy,"Fy_kN":Fy,"Ductility":duct}

def cycles(disp, force):
    d = pd.Series(np.sign(np.where(np.diff(disp)==0, np.nan, np.diff(disp)))).ffill().bfill().to_numpy()
    turn = np.ones(len(disp), dtype=bool); turn[1:-1] = d[1:] != d[:-1]; turn[0]=turn[-1]=True
    idx = np.where(turn)[0]
    peaks = [k for k in idx if disp[k]>0]
    cyc = []
    for c, (i0,i1) in enumerate(zip(peaks[:-1], peaks[1:]), 1):
        sd, sf = disp[i0:i1+1], force[i0:i1+1]
        if len(sd)<3: continue
        ip, iN = np.argmax(sf), np.argmin(sf)
        cyc.append({"cycle":c,"disp":sd,"force":sf,"peak_pos_disp":float(sd[ip]),
                    "peak_pos_force":float(sf[ip]),"peak_neg_disp":float(sd[iN]),
                    "peak_neg_force":float(sf[iN])})
    return cyc

def cycle_metrics(cyc):
    if not cyc: return None
    cn = np.array([c["cycle"] for c in cyc])
    stiff = np.array([(c["peak_pos_force"]-c["peak_neg_force"])/(c["peak_pos_disp"]-c["peak_neg_disp"])
                      if c["peak_pos_disp"]!=c["peak_neg_disp"] else np.nan for c in cyc])
    pct = 100*stiff/stiff[0] if len(stiff) else np.array([])
    eng = []
    for c in cyc:
        x,y = c["disp"], c["force"]
        xc,yc = np.concatenate([x,x[:1]]), np.concatenate([y,y[:1]])
        eng.append(0.5*np.abs(np.sum(xc[:-1]*yc[1:]-xc[1:]*yc[:-1])))
    eng = np.array(eng)
    return {"cycle_number":cn,"stiffness_kN_per_mm":stiff,"stiffness_pct_of_initial":pct,
            "energy_kN_mm":eng,"cumulative_energy_kN_mm":np.cumsum(eng)}

def save_plots(stem, dirs, data):
    """Save all plots for a specimen"""
    d, f, bx, by, px, py, nx, ny = data['disp'], data['force'], data['bx'], data['by'], data['pos_x'], data['pos_y'], data['neg_x'], data['neg_y']
    mx, my, g, avg, p_avg = data['mirror_x'], data['mirror_y'], data['grid'], data['avg_y'], data['props_avg']
    cm = data['cycle_metrics']
    
    # Create specimen subfolder in each category
    spec_backbone_plots = os.path.join(dirs["backbone_plots"], stem)
    spec_pna_plots = os.path.join(dirs["pna_plots"], stem)
    spec_bilinear_plots = os.path.join(dirs["bilinear_plots"], stem)
    spec_stiffness_plots = os.path.join(dirs["stiffness_plots"], stem)
    spec_energy_plots = os.path.join(dirs["energy_plots"], stem)
    
    os.makedirs(spec_backbone_plots, exist_ok=True)
    os.makedirs(spec_pna_plots, exist_ok=True)
    os.makedirs(spec_bilinear_plots, exist_ok=True)
    os.makedirs(spec_stiffness_plots, exist_ok=True)
    os.makedirs(spec_energy_plots, exist_ok=True)
    
    # 1. Backbone plot
    fig, ax = plt.subplots(figsize=(10,8))
    ax.plot(d, f, color="lightgray", linewidth=0.8, label="Raw data")
    ax.plot(bx, by, color="crimson", linewidth=2.5, marker="o", markersize=4, label="Backbone")
    ax.axhline(0, color="black", linewidth=0.6); ax.axvline(0, color="black", linewidth=0.6)
    ax.set_xlabel("Displacement (mm)"); ax.set_ylabel("Force (kN)"); ax.set_title(f"Backbone: {stem}")
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(spec_backbone_plots, f"{stem}_backbone.png"), dpi=200)
    plt.close()
    
    # 2. Positive/Negative/Average plot
    fig, ax = plt.subplots(figsize=(10,8))
    ax.plot(px, py, color="royalblue", linewidth=2, marker="o", markersize=4, label="Positive")
    ax.plot(mx, my, color="darkorange", linewidth=2, marker="o", markersize=4, label="Negative (mirrored)")
    ax.plot(g, avg, color="black", linewidth=2.5, linestyle="--", label="Average")
    ax.axhline(0, color="black", linewidth=0.6); ax.axvline(0, color="black", linewidth=0.6)
    ax.set_xlim(left=0); ax.set_ylim(bottom=0)
    ax.set_xlabel("Displacement (mm)"); ax.set_ylabel("Force (kN)"); ax.set_title(f"Branches: {stem}")
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(spec_pna_plots, f"{stem}_branches.png"), dpi=200)
    plt.close()
    
    # 3. Bilinear idealization plot
    bl = data['bilinear']
    fig, ax = plt.subplots(figsize=(10,8))
    ax.plot(g, avg, color="black", linewidth=2, label="Average backbone")
    if bl is not None:
        bl_x, bl_y = bl
        ax.plot(bl_x, bl_y, color="seagreen", linewidth=2.5, linestyle="--", marker="s", markersize=6, label="Bilinear (EEEP)")
        ax.scatter([p_avg["Dmax_mm"]], [p_avg["Fmax_kN"]], color="red", zorder=5, s=50, label=f"Peak ({p_avg['Dmax_mm']:.2f}, {p_avg['Fmax_kN']:.2f})")
        ax.scatter([p_avg["Du_mm"]], [p_avg["Fu_kN"]], color="purple", zorder=5, s=50, label=f"Ultimate ({p_avg['Du_mm']:.2f}, {p_avg['Fu_kN']:.2f})")
    ax.axhline(0, color="black", linewidth=0.6); ax.axvline(0, color="black", linewidth=0.6)
    ax.set_xlim(left=0); ax.set_ylim(bottom=0)
    ax.set_xlabel("Displacement (mm)"); ax.set_ylabel("Force (kN)"); ax.set_title(f"Bilinear: {stem}")
    ax.legend(fontsize=9); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(spec_bilinear_plots, f"{stem}_bilinear.png"), dpi=200)
    plt.close()
    
    # 4. Stiffness degradation and energy plots (if cycles exist)
    if cm is not None:
        # Stiffness degradation
        fig, ax = plt.subplots(figsize=(10,8))
        ax.bar(cm["cycle_number"], cm["stiffness_kN_per_mm"], color="#2f8fd6", edgecolor="black")
        ax.set_xlabel("Cycle number"); ax.set_ylabel("Secant stiffness (kN/mm)")
        ax.set_title(f"Stiffness Degradation: {stem}"); ax.grid(alpha=0.3, axis="y")
        plt.tight_layout()
        plt.savefig(os.path.join(spec_stiffness_plots, f"{stem}_stiffness.png"), dpi=200)
        plt.close()
        
        # Energy per loop
        fig, ax = plt.subplots(figsize=(10,8))
        ax.bar(cm["cycle_number"], cm["energy_kN_mm"], color="#e08a2f", edgecolor="black")
        ax.set_xlabel("Cycle number"); ax.set_ylabel("Energy per loop (kN·mm)")
        ax.set_title(f"Energy per Loop: {stem}"); ax.grid(alpha=0.3, axis="y")
        plt.tight_layout()
        plt.savefig(os.path.join(spec_energy_plots, f"{stem}_energy_per_loop.png"), dpi=200)
        plt.close()
        
        # Cumulative energy
        fig, ax = plt.subplots(figsize=(10,8))
        ax.bar(cm["cycle_number"], cm["cumulative_energy_kN_mm"], color="#3d9c6c", edgecolor="black")
        ax.set_xlabel("Cycle number"); ax.set_ylabel("Cumulative energy (kN·mm)")
        ax.set_title(f"Cumulative Energy: {stem}"); ax.grid(alpha=0.3, axis="y")
        plt.tight_layout()
        plt.savefig(os.path.join(spec_energy_plots, f"{stem}_cumulative_energy.png"), dpi=200)
        plt.close()

def save_csvs(stem, dirs, data):
    """Save all CSV files for a specimen in sub-sub folders"""
    # Create specimen subfolder in each CSV category
    spec_backbone_csv = os.path.join(dirs["backbone_csv"], stem)
    spec_pna_csv = os.path.join(dirs["pna_csv"], stem)
    spec_bilinear_csv = os.path.join(dirs["bilinear_csv"], stem)
    spec_stiffness_csv = os.path.join(dirs["stiffness_csv"], stem)
    spec_energy_csv = os.path.join(dirs["energy_csv"], stem)
    
    os.makedirs(spec_backbone_csv, exist_ok=True)
    os.makedirs(spec_pna_csv, exist_ok=True)
    os.makedirs(spec_bilinear_csv, exist_ok=True)
    os.makedirs(spec_stiffness_csv, exist_ok=True)
    os.makedirs(spec_energy_csv, exist_ok=True)
    
    # Backbone CSV
    pd.DataFrame({"displacement_mm": data['bx'], "force_kN": data['by']}).to_csv(
        os.path.join(spec_backbone_csv, f"{stem}_backbone.csv"), index=False)
    
    # Branches CSV
    pd.DataFrame({
        "displacement_mm": data['pos_x'], 
        "positive_force_kN": data['pos_y'],
        "mirrored_neg_force_kN": data['mirror_y']
    }).to_csv(os.path.join(spec_pna_csv, f"{stem}_positive.csv"), index=False)
    
    # Average branch CSV
    pd.DataFrame({"displacement_mm": data['grid'], "avg_force_kN": data['avg_y']}).to_csv(
        os.path.join(spec_pna_csv, f"{stem}_average.csv"), index=False)
    
    # Bilinear CSV
    if data['bilinear'] is not None:
        bl_x, bl_y = data['bilinear']
        pd.DataFrame({"displacement_mm": bl_x, "force_kN": bl_y}).to_csv(
            os.path.join(spec_bilinear_csv, f"{stem}_bilinear.csv"), index=False)
    
    # Cycle metrics CSVs
    if data['cycle_metrics'] is not None:
        cm = data['cycle_metrics']
        # Stiffness degradation CSV
        pd.DataFrame({
            "cycle": cm["cycle_number"],
            "stiffness_kN_per_mm": cm["stiffness_kN_per_mm"],
            "stiffness_pct_of_initial": cm["stiffness_pct_of_initial"]
        }).to_csv(os.path.join(spec_stiffness_csv, f"{stem}_stiffness.csv"), index=False)
        
        # Energy dissipation CSV
        pd.DataFrame({
            "cycle": cm["cycle_number"],
            "energy_per_loop_kN_mm": cm["energy_kN_mm"],
            "cumulative_energy_kN_mm": cm["cumulative_energy_kN_mm"]
        }).to_csv(os.path.join(spec_energy_csv, f"{stem}_energy.csv"), index=False)

def process_one(path, dirs):
    """Process a single file and save all outputs"""
    stem = os.path.splitext(os.path.basename(path))[0]
    d, f = load_data(path)
    bx, by, px, py, nx, ny = backbone(d, f)
    mx, my = mirror(nx, ny)
    g, avg = average(px, py, mx, my)
    p_avg = properties(g, avg)
    
    # Bilinear idealization
    bl = (np.array([0, p_avg["Dy_mm"], p_avg["Du_mm"]]), 
          np.array([0, p_avg["Fy_kN"], p_avg["Fy_kN"]])) if np.isfinite(p_avg.get("Dy_mm", np.nan)) else None
    
    # Cycle metrics
    cm = cycle_metrics(cycles(d, f))
    
    # Collect data for saving
    data = {
        'disp': d, 'force': f, 'bx': bx, 'by': by, 'pos_x': px, 'pos_y': py,
        'neg_x': nx, 'neg_y': ny, 'mirror_x': mx, 'mirror_y': my,
        'grid': g, 'avg_y': avg, 'props_avg': p_avg, 'bilinear': bl,
        'cycle_metrics': cm
    }
    
    # Save plots and CSVs
    save_plots(stem, dirs, data)
    save_csvs(stem, dirs, data)
    
    # Build summary row
    row = {"Specimen": stem}
    for k,v in properties(px,py).items(): row[f"Pos_{k}"] = v
    for k,v in properties(mx,my).items(): row[f"Neg_{k}"] = v
    for k,v in p_avg.items(): row[f"Avg_{k}"] = v
    if cm:
        row["Num_Cycles"] = len(cm["cycle_number"])
        row["Total_Energy_kN_mm"] = float(cm["cumulative_energy_kN_mm"][-1])
        row["Final_Stiffness_Pct"] = float(cm["stiffness_pct_of_initial"][-1])
    else:
        row.update({"Num_Cycles":0, "Total_Energy_kN_mm":np.nan, "Final_Stiffness_Pct":np.nan})
    
    return row

def process_all(output_dir="results"):
    """Process all .txt files in current directory with organized output"""
    files = sorted(glob.glob("*.txt"))
    if not files: raise ValueError("No .txt files found in current directory")
    
    # Create folder structure
    dirs = {}
    for key, subdir in FOLDERS.items():
        path = os.path.join(output_dir, subdir)
        os.makedirs(path, exist_ok=True)
        dirs[key] = path
    
    rows = []
    print(f"\n{'='*60}")
    print(f"Processing {len(files)} files...")
    print(f"{'='*60}\n")
    
    for path in files:
        try:
            row = process_one(path, dirs)
            rows.append(row)
            print(f"[OK] {os.path.basename(path)}")
        except Exception as e:
            print(f"[FAIL] {os.path.basename(path)}: {e}")
    
    # Save summary
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(os.path.join(dirs["summary"], "master_summary.csv"), index=False)
        print(f"\n{'='*60}")
        print(f"✓ Processed: {len(rows)} succeeded, {len(files)-len(rows)} failed")
        print(f"✓ Results saved to: {os.path.abspath(output_dir)}")
        print(f"✓ Summary: {os.path.join(dirs['summary'], 'master_summary.csv')}")
        print(f"{'='*60}\n")
        return df
    return pd.DataFrame()

# Run it - automatically processes all .txt files in current directory
if __name__ == "__main__":
    summary_df = process_all()
