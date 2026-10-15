% ca-capstone.cls — capstone project (мини-курсовая) specification.
%
%   \capstonetitle{<title>}  — bold title line
%   Standard sections (unnumbered, compact):
%     \goal, \functionality, \requirements, \details, \schedule, \remarks, \references
%   each is a shortcut for \section*{<Russian heading>}.
%
% References come from the shared bibliography (latex/ca-refs.bib, biblatex):
%   \capstonerefs{key1,key2,...}  — in the preamble or right after \begin{document}:
%                                  fixes the numbering of the reference list (the order
%                                  of the original spec), whether or not an entry is cited
%   \cite{key} / \cite[locator]{key} in the text
%   \references                  — the "Полезные источники" heading + the list
%
% Measured requirements: each capstone directory holds a generated requirements.tex
% (taskgen.capstone report) with \Req... macros; spec.tex does \input{requirements}.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ca-capstone}[2026/10/14 Computer Algebra capstone project spec]

\DeclareOption*{\PassOptionsToClass{\CurrentOption}{extarticle}}
\PassOptionsToClass{11pt,a4paper}{extarticle}
\ProcessOptions\relax
\LoadClass{extarticle}

\RequirePackage[notheorems]{ca-common}
\RequirePackage[a4paper,margin=20mm]{geometry}
\RequirePackage{ca-biblio}
\RequirePackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=magenta,citecolor=blue}
\RequirePackage{xurl}
\pagestyle{plain}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.35em}

\makeatletter
\renewcommand\section{\@startsection{section}{1}{\z@}%
  {-1.4ex \@plus -.5ex \@minus -.2ex}{0.5ex}{\normalfont\large\bfseries}}
% Footnotes: the "why?" questions of the specs are footnoted; keep them compact.
\setlength{\skip\footins}{1.2em plus 0.4em}
\makeatother

\newcommand{\capstonetitle}[1]{%
  {\noindent\Large\bfseries #1\par}\smallskip
  \noindent\textcolor{caBlue}{\rule{\linewidth}{0.8pt}}\par}

\newcommand{\capstonerefs}[1]{\AtBeginDocument{\nocite{#1}}}

\defbibheading{capstone}[\bibname]{\section*{#1}}
\newcommand{\goal}{\section*{Цель работы}}
\newcommand{\functionality}{\section*{Требуемый функционал}}
\newcommand{\requirements}{\section*{Требования к реализации}}
\DeclareRobustCommand{\details}{\section*{Детали реализации}}
\newcommand{\schedule}{\section*{Сроки и порядок выполнения работы}}
\newcommand{\remarks}{\section*{Замечания}}
\DeclareRobustCommand{\references}{%
  \printbibliography[heading=capstone,title={Полезные источники}]}

\endinput
