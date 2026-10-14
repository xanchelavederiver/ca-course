% ca-slides.cls — lecture slides: beamer 16:9 + the "ca" canvas theme.
%
%   \documentclass{ca-slides}            % any beamer option is passed through
%   \lecture{<number>}{<title>}           % sets title/short title/subtitle
%   \begin{document} \titleframe ...
%
% Slides carry definitions, statements and figures; proofs are written live:
%   \aside{<text>}                — side question/remark (red, right half)
%   \proofarea[<height>]          — «Доказательство:» label + free space for the pen
%   \begin{theoremframe}[<env>]{<frame title>} <statement> \end{theoremframe}
%                                  — a top-aligned frame with one theorem-like block
%                                    (<env> = theorem (default), lemma, proposition,
%                                    corollary, definition, ...) and a proof area
%                                    filling the rest of the frame
% Figures and traces shared with the notes: ca-figures.sty (\xgcdtable, \rhoshape,
% \ecaddfigure, \latticefigure, ...).
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ca-slides}[2026/10/13 Computer Algebra lecture slides]

\DeclareOption*{\PassOptionsToClass{\CurrentOption}{beamer}}
\PassOptionsToClass{aspectratio=169,12pt}{beamer}
\ProcessOptions\relax
\LoadClass{beamer}

\RequirePackage[notheorems]{ca-common}
\usetheme{ca}
\RequirePackage{ca-figures}

% beamer defines theorem/lemma/definition/...; add the remaining ones.
\newtheorem{proposition}[theorem]{Утверждение}
\theoremstyle{remark}
\newtheorem{remark}[theorem]{Замечание}
\theoremstyle{definition}
\newtheorem{algorithm}[theorem]{Алгоритм}
\theoremstyle{plain}

\newcommand{\coursename}{Компьютерная алгебра}
\renewcommand{\lecture}[2]{%
  \title{#2}%
  \subtitle{\coursename. Лекция~#1}%
  \date{}%
}
% \aside{text} — a margin-style question/remark (the callouts of the PPTX decks)
\newcommand{\aside}[1]{%
  \par\hfill\begin{minipage}[t]{0.42\linewidth}\raggedright\small
    \textcolor{caRed}{\textbf{?}~\itshape #1}\end{minipage}\par}

\newcommand{\proofarea}[1][0.3\textheight]{%
  \par\smallskip{\small\textcolor{caGray}{Доказательство:}}\penspace[#1]}

\NewDocumentEnvironment{theoremframe}{O{theorem} m +b}{%
  \begin{frame}[t]{#2}
    \begin{#1}#3\end{#1}
    \par\smallskip{\small\textcolor{caGray}{Доказательство:}}\vfill
  \end{frame}%
}{}

\newcommand{\titleframe}{\begin{frame}[plain]\titlepage\end{frame}}

\endinput
