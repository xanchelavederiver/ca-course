% ca-notes.cls — lecture notes for the Computer Algebra course.
%
% Thin wrapper over extarticle (12pt by default; any extarticle size option
% is passed through). Adds a lecture title block, numbered theorem-like
% environments (from ca-common), "check yourself" questions and a
% further-reading section.
%
%   \lecture{<number>}{<title>}   — sets the title block data
%   \makelecturetitle             — typesets the title block
%   \checkyourself{...}           — inline question (collected)
%   \checkyourselfsection         — section listing all collected questions
%   \begin{furtherreading} \item ... \end{furtherreading}
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ca-notes}[2026/10/13 Computer Algebra lecture notes]

\DeclareOption*{\PassOptionsToClass{\CurrentOption}{extarticle}}
\PassOptionsToClass{12pt,a4paper}{extarticle}
\ProcessOptions\relax
\LoadClass{extarticle}

\RequirePackage{ca-common}
\RequirePackage[a4paper,width=165mm,top=22mm,bottom=25mm]{geometry}
\RequirePackage{fancyhdr}
\RequirePackage[hidelinks]{hyperref}
\RequirePackage{bookmark}

\newcommand{\coursename}{Компьютерная алгебра}
\newcommand{\ca@lecnum}{??}
\newcommand{\ca@lectitle}{Без названия}
\newcommand{\lecture}[2]{\renewcommand{\ca@lecnum}{#1}\renewcommand{\ca@lectitle}{#2}}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\textcolor{caGray}{\coursename}}
\fancyhead[R]{\small\textcolor{caGray}{Лекция~\ca@lecnum}}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.4pt}

\newcommand{\makelecturetitle}{%
  \begin{center}
    {\large\textcolor{caGray}{\coursename}}\par\smallskip
    {\LARGE\bfseries Лекция~\ca@lecnum. \ca@lectitle\par}
    \medskip\textcolor{caBlue}{\rule{0.6\linewidth}{0.8pt}}
  \end{center}
  \bigskip
}

\newcommand{\checkyourselfsection}{%
  \section*{Вопросы для самопроверки}
  \addcontentsline{toc}{section}{Вопросы для самопроверки}
  \printcheckyourself
}

\newenvironment{furtherreading}{%
  \section*{Литература и дополнительные материалы}
  \addcontentsline{toc}{section}{Литература и дополнительные материалы}
  \begin{enumerate}[label={[\arabic*]}]%
}{%
  \end{enumerate}%
}

\endinput
