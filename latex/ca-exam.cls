% ca-exam.cls — exam (зачёт / экзамен) question sheets.
%
% One source produces both PDFs: the plain question list and the variant
% with references (option `refs`).
%
%   \examtitle[<genitive>]{<title>}{<date>}
%       e.g. [вопросов на зачёт]{Вопросы на зачёт}{декабрь 2025}
%   \begin{literature} \item ... \end{literature}  — shown only with `refs`
%   \topic{<topic title>}          — topic heading; numbering continues
%   \question{<text>}{<refs>}      — refs shown only with `refs`
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ca-exam}[2026/10/13 Computer Algebra exam questions]

\newif\ifrefs \refsfalse
\DeclareOption{refs}{\refstrue}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{extarticle}}
\PassOptionsToClass{12pt,a4paper}{extarticle}
\ProcessOptions\relax
\LoadClass{extarticle}

\RequirePackage[notheorems]{ca-common}
\RequirePackage[a4paper,width=170mm,top=18mm,bottom=20mm]{geometry}
\RequirePackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=magenta}
\RequirePackage{xurl}
\pagestyle{plain}
\setlength{\parindent}{0pt}

\newcommand{\coursename}{Компьютерная алгебра}

\newcommand{\examtitle}[3][]{%
  \begin{center}
    \ifrefs
      {\Large\bfseries Ссылки на источники для\\[0.2em]
       \ifx\relax#1\relax #2\else #1\fi\ по курсу \coursename}%
    \else
      {\Large\bfseries #2 по курсу \coursename}%
    \fi
    \par\smallskip
    {\normalsize #3}
  \end{center}\medskip
}

\newenvironment{literature}{%
  \ifrefs\subsection*{Литература}\else\setbox0\vbox\bgroup\fi
  \begin{enumerate}[label={\arabic*.}]%
}{%
  \end{enumerate}%
  \ifrefs\else\egroup\fi
}

\newcounter{examquestion}
\newcommand{\topic}[1]{%
  \par\bigskip{\large\bfseries #1}\par\smallskip}
\newcommand{\question}[2]{%
  \refstepcounter{examquestion}%
  \par\noindent\hangindent=2em\hangafter=1
  \makebox[2em][l]{\theexamquestion.}#1%
  \ifrefs\par\noindent\hspace*{2em}\textcolor{caGray}{#2}\fi
  \par\smallskip
}

\endinput
