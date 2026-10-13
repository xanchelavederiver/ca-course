% ca-slides.cls — lecture slides: beamer 16:9 + the "ca" canvas theme.
%
%   \documentclass{ca-slides}            % any beamer option is passed through
%   \lecture{<number>}{<title>}           % sets title/short title/subtitle
%   \begin{document} \titleframe ...
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ca-slides}[2026/10/13 Computer Algebra lecture slides]

\DeclareOption*{\PassOptionsToClass{\CurrentOption}{beamer}}
\PassOptionsToClass{aspectratio=169,12pt}{beamer}
\ProcessOptions\relax
\LoadClass{beamer}

\RequirePackage[notheorems]{ca-common}
\usetheme{ca}

% beamer defines theorem/lemma/definition/...; add the remaining ones.
\newtheorem{proposition}[theorem]{Утверждение}
\theoremstyle{remark}
\newtheorem{remark}[theorem]{Замечание}
\theoremstyle{plain}

\newcommand{\coursename}{Компьютерная алгебра}
\renewcommand{\lecture}[2]{%
  \title{#2}%
  \subtitle{\coursename. Лекция~#1}%
  \date{}%
}
\newcommand{\titleframe}{\begin{frame}[plain]\titlepage\end{frame}}

\endinput
