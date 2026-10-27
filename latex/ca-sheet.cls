% ca-sheet.cls — task sheets and solution manuals (classroom, homework, exam).
%
% Mirrors the layout of the legacy контрольная documents: extarticle 14pt,
% 170mm text width, unnumbered sections/subsections that still appear in
% the table of contents.
%
% Options:
%   solutions   — typeset \solution{...} blocks (answer key / solution manual)
%   <size>      — any extarticle size option (default 14pt)
%
%   \solution{...}  — printed only with the `solutions` option
%   \ifsolutions ... \fi — for arbitrary conditional content
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ca-sheet}[2026/10/13 Computer Algebra task sheets]

\newif\ifsolutions \solutionsfalse
\DeclareOption{solutions}{\solutionstrue}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{extarticle}}
\PassOptionsToClass{14pt,a4paper}{extarticle}
\ProcessOptions\relax
\LoadClass{extarticle}

\RequirePackage{ca-common}
\RequirePackage[a4paper,width=170mm,top=20mm,bottom=20mm]{geometry}
\pagestyle{plain}
% Solutions contain long inline formulas: allow looser lines and page breaks in displays.
\setlength{\emergencystretch}{3em}
\allowdisplaybreaks

% Unnumbered (but listed in the ToC) sections, as in the legacy sheets.
\renewcommand\thesection{}
\renewcommand\thesubsection{}
% The sections stay *numbered* as far as LaTeX is concerned (so they reach the
% ToC), and the default \@seccntformat typesets "\thesection\quad" — with an
% empty \thesection that is a bare \quad indenting every heading by ~1em.
% Drop the separator so headings are flush with the body text.
\renewcommand*\@seccntformat[1]{}
% Same in the ToC: \contentsline wraps the (empty) number in \numberline, a box
% 1.5em/2.3em wide that pushes every entry right. Drop the box — the entries are
% then flush too, and the section/subsection hierarchy step (\leftskip) remains.
\renewcommand*\numberline[1]{}

\RequirePackage{hyperref}
\hypersetup{
  colorlinks=true,
  linkcolor=blue,
  citecolor=blue,
  urlcolor=magenta
}
\RequirePackage{bookmark}

\newcommand{\solutionname}{Решение}
\newcommand{\answername}{Ответ}
\newcommand{\solution}[1]{%
  \ifsolutions\par\nopagebreak\noindent\textbf{\solutionname}: #1\fi}

% Header line for the variant/sheet: \sheettitle{Контрольная работа}
\newcommand{\sheettitle}[1]{\section*{#1}}

\endinput
