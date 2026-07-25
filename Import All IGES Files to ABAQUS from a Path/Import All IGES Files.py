# -*- coding: mbcs -*-

# Developer: Tufail Mabood
# WhatsApp: +923440907874
# Note:
# - I have not yet checked the surface import feature in it.

# Folder containing all IGES files
FOLDER = r"Path of .iges files"

import os

from abaqus import *
from abaqusConstants import *
from caeModules import *

# Create Model-1 if it doesn't exist
if not mdb.models.has_key('Model-1'):
    mdb.Model(name='Model-1')

model = mdb.models['Model-1']

# Loop through all IGES files
for filename in os.listdir(FOLDER):

    if filename.lower().endswith((".igs", ".iges")):

        filepath = os.path.join(FOLDER, filename)
        part_name = os.path.splitext(filename)[0]

        print "Importing:", filename

        # First try importing as a solid/surface
        try:

            iges = mdb.openIges(
                filepath,
                msbo=False,
                trimCurve=DEFAULT,
                scaleFromFile=OFF
            )

            model.PartFromGeometryFile(
                name=part_name,
                geometryFile=iges,
                combine=False,
                stitchTolerance=1.0,
                dimensionality=THREE_D,
                type=DEFORMABLE_BODY,
                convertToAnalytical=1,
                stitchEdges=1
            )

            print "  Imported as SOLID/SURFACE"

        # If that fails, try importing as wire geometry
        except:

            print "  Trying as WIRE..."

            try:

                iges = mdb.openIges(
                    filepath,
                    msbo=False,
                    trimCurve=DEFAULT,
                    topology=WIRE,
                    scaleFromFile=OFF
                )

                model.PartFromGeometryFile(
                    name=part_name,
                    geometryFile=iges,
                    combine=False,
                    stitchTolerance=1.0,
                    dimensionality=THREE_D,
                    type=DEFORMABLE_BODY,
                    topology=WIRE,
                    convertToAnalytical=1,
                    stitchEdges=1
                )

                print "  Imported as WIRE"

            except:

                print "  FAILED TO IMPORT:", filename

print "----------------------------------------"
print "Finished importing all IGES files."
print "----------------------------------------"
