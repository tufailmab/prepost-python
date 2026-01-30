import math

# User inputs (from tests)

E_parallel = 8018.5      # MPa  (E along grain)
E_perp = 481             # MPa  (E perpendicular to grain - radial)

# Typical orthotropic ratios for wood
E3_ratio = 1             # E_tangential ≈ 0.5 * E_radial

# Ref: https://www.researchgate.net/profile/George-Papazafeiropoulos/post/What_type_of_plasticity_model_and_its_data_for_wood_material_should_be_input_in_ABAQUS_software/attachment/61f30ac4d248c650edc357e4/AS%3A1116970619535361%401643317956489/download/howtomodelwoodinabaqus.pdf
# Table 1. Material properties used in the analysis. 
# The directions considered follow similar range (Prop 4,5 & 6)
nu12 = 0.04              # nu_LR
nu13 = 0.04              # nu_LT
nu23 = 0.40              # nu_RT

# Shear empirical relations
# Ref: https://www.researchgate.net/publication/393092166_Estimation_of_longitudinal_and_transverse_elastic_moduli_of_native_Brazilian_woods_by_static_bending_tests
def shear_L(E):
    return E / 16

def shear_RT(E):
    return E / 10

# Derived Elastic Constants
# For Direction
# Ref: https://www.sciencedirect.com/science/article/pii/S0141029625004250
# Sec: 4.2.1. Beechlaminatedveneer lumber
E1 = E_parallel                 # Longitudinal
E2 = E_perp                     # Radial
E3 = E2 * E3_ratio              # Tangential

G12 = shear_L(E1)
G13 = shear_L(E1)
G23 = shear_RT(E2)

# Reciprocal Poisson ratios (from symmetry)
nu21 = nu12 * E2 / E1
nu31 = nu13 * E3 / E1
nu32 = nu23 * E3 / E2

# Stability Checks
# https://classes.engineering.wustl.edu/2009/spring/mase5513/abaqus/docs/v6.6/books/usb/default.htm?startat=pt05ch17s02abm02.html
check1 = abs(nu12) < math.sqrt(E1 / E2)
check2 = abs(nu13) < math.sqrt(E1 / E3)
check3 = abs(nu23) < math.sqrt(E2 / E3)

D = (1
     - nu12 * nu21
     - nu23 * nu32
     - nu31 * nu13
     - 2 * nu21 * nu32 * nu13)


# Outputs
print("\n=== ORTHOTROPIC ELASTIC CONSTANTS ===")
print(f"E1 (Longitudinal)  = {E1:.2f} MPa")
print(f"E2 (Radial)        = {E2:.2f} MPa")
print(f"E3 (Tangential)    = {E3:.2f} MPa\n")

print(f"G12 = {G12:.2f} MPa")
print(f"G13 = {G13:.2f} MPa")
print(f"G23 = {G23:.2f} MPa\n")

print("Poisson Ratios:")
print(f"nu12 = {nu12:.4f}")
print(f"nu13 = {nu13:.4f}")
print(f"nu23 = {nu23:.4f}")
print(f"nu21 = {nu21:.6f}")
print(f"nu31 = {nu31:.6f}")
print(f"nu32 = {nu32:.6f}\n")

print("=== STABILITY CONDITIONS ===")
print(f"E1,E2,E3,G12,G13,G23 > 0 :  {all(x>0 for x in [E1,E2,E3,G12,G13,G23])}")
print(f"|nu12| < sqrt(E1/E2)      :  {check1}")
print(f"|nu13| < sqrt(E1/E3)      :  {check2}")
print(f"|nu23| < sqrt(E2/E3)      :  {check3}")

print("\nDeterminant condition (incompressibility measure):")
print(f"D = {D:.5f}")

if D > 0:
    print("Material is stable (positive definite).")
else:
    print("Material is NOT stable!")

if D < 0.05:
    print("Material is approaching incompressible behaviour.")
else:
    print("Material is FAR from incompressible (highly compressible).")
