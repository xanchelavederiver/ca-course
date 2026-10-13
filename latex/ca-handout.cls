% ca-handout.cls — 1–2 page seminar handout (theory reminder).
%
%   \seminar{<number>}{<title>}  — sets the header data
%   \makehandouttitle            — compact title line
%   \begin{reminder}...\end{reminder} — framed box for key formulas
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ca-handout}[2026/10/13 Computer Algebra seminar handout]

\DeclareOption*{\PassOptionsToClass{\CurrentOption}{extarticle}}
\PassOptionsToClass{11pt,a4paper}{extarticle}
\ProcessOptions\relax
\LoadClass{extarticle}

\RequirePackage{ca-common}
\RequirePackage[a4paper,margin=17mm,top=15mm,bottom=18mm]{geometry}
\RequirePackage[hidelinks]{hyperref}
\RequirePackage[most]{tcolorbox}

\newcommand{\coursename}{Компьютерная алгебра}
\newcommand{\ca@semnum}{??}
\newcommand{\ca@semtitle}{Без названия}
\newcommand{\seminar}[2]{\renewcommand{\ca@semnum}{#1}\renewcommand{\ca@semtitle}{#2}}

\pagestyle{plain}
\setlength{\parskip}{0.3em}
\setlength{\parindent}{0pt}

\newcommand{\makehandouttitle}{%
  \noindent{\small\textcolor{caGray}{\coursename\hfill Семинар~\ca@semnum}}\par
  \noindent{\Large\bfseries \ca@semtitle}\par
  \noindent\textcolor{caBlue}{\rule{\linewidth}{0.8pt}}\par\medskip
}

\newtcolorbox{reminder}[1][]{%
  colback=caLight, colframe=caBlue, boxrule=0.6pt, arc=1mm,
  left=2mm, right=2mm, top=1mm, bottom=1mm,
  fonttitle=\bfseries, #1}

% Handouts are compact: tighter section spacing.
\makeatletter
\renewcommand\section{\@startsection{section}{1}{\z@}%
  {-1.2ex \@plus -.5ex \@minus -.2ex}{0.6ex}{\normalfont\large\bfseries}}
\renewcommand\subsection{\@startsection{subsection}{2}{\z@}%
  {-1ex \@plus -.4ex \@minus -.2ex}{0.4ex}{\normalfont\normalsize\bfseries}}
\makeatother

\endinput
