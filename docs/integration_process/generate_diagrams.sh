set -euo pipefail
OUTDIR="/home/user/projects/sbd-drones-economics/sbd-drones-economics-ai/docs/integration_process/diagrams"
JAVA_TOOL_OPTIONS='-Djava.awt.headless=true' DISPLAY='' plantuml -tpng -o "$OUTDIR" /home/user/projects/sbd-drones-economics/sbd-drones-economics-ai/docs/integration_process/model_description_extended_diagrams.puml > /tmp/plantuml_regen3.log 2>&1
ls -1 "$OUTDIR" | wc -l
