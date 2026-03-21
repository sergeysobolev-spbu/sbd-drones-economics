export JAVA_TOOL_OPTIONS ?= -Djava.awt.headless=true

diagrams:
	plantuml -tpng images/*.puml

slides: diagrams
	xelatex sbom.tex
	xelatex sbom.tex