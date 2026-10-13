% ca-capstone.cls — capstone project (мини-курсовая) specification.
%
%   \capstonetitle{<title>}  — bold title line
%   Standard sections (unnumbered, compact):
%     \goal, \functionality, \requirements, \details, \schedule, \references
%   each is a shortcut for \section*{<Russian heading>}.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ca-capstone}[2026/10/13 Computer Algebra capstone project spec]

\DeclareOption*{\PassOptionsToClass{\CurrentOption}{extarticle}}
\PassOptionsToClass{11pt,a4paper}{extarticle}
\ProcessOptions\relax
\LoadClass{extarticle}

\RequirePackage[notheorems]{ca-common}
\RequirePackage[a4paper,margin=20mm]{geometry}
\RequirePackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=magenta}
\RequirePackage{xurl}
\pagestyle{plain}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.35em}

\makeatletter
\renewcommand\section{\@startsection{section}{1}{\z@}%
  {-1.4ex \@plus -.5ex \@minus -.2ex}{0.5ex}{\normalfont\large\bfseries}}
\makeatother

\newcommand{\capstonetitle}[1]{%
  {\noindent\Large\bfseries #1\par}\smallskip
  \noindent\textcolor{caBlue}{\rule{\linewidth}{0.8pt}}\par}

\newcommand{\goal}{\section*{Цель работы}}
\newcommand{\functionality}{\section*{Требуемый функционал}}
\newcommand{\requirements}{\section*{Требования к реализации}}
\DeclareRobustCommand{\details}{\section*{Детали реализации}}
\newcommand{\schedule}{\section*{Сроки и порядок выполнения работы}}
\DeclareRobustCommand{\references}{\section*{Ссылки}}

\endinput
