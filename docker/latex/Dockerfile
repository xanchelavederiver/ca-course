# LaTeX toolchain for all course materials.
# pdfLaTeX + T2A/utf8 (Cyrillic via cm-super), latexmk, beamer, extsizes.
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      texlive-latex-base \
      texlive-latex-recommended \
      texlive-latex-extra \
      texlive-fonts-recommended \
      texlive-lang-cyrillic \
      texlive-pictures \
      texlive-science \
      cm-super \
      lmodern \
      latexmk \
      make \
      poppler-utils \
      ghostscript \
 && rm -rf /var/lib/apt/lists/*

# Reproducible PDFs: fixed timestamps / IDs unless overridden.
ENV SOURCE_DATE_EPOCH=0 \
    FORCE_SOURCE_DATE=1 \
    TEXMFVAR=/tmp/texmf-var \
    HOME=/tmp

WORKDIR /work
