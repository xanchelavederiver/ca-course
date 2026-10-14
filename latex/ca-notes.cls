% ca-notes.cls — lecture notes for the Computer Algebra course.
%
% A lecture's text lives in notes-body.tex so that it compiles both standalone
% (notes.tex, a thin wrapper) and as a chapter of the semester book
% (`make book SEM=N`, class option `book`):
%
%   notes.tex:       \documentclass{ca-notes}
%                    \begin{document}\input{notes-body}\end{document}
%   notes-body.tex:  \begin{lecture}{<number>}{<title>}
%                      \section{...} ... \checkyourself{...} ...
%                      \checkyourselfsection
%                      \begin{furtherreading}
%                        \readitem[<locator>]{<bib key>}{<comment>}
%                      \end{furtherreading}
%                    \end{lecture}
%
% Standalone: extarticle (12pt), title block + table of contents; the further
% reading list is followed by the lecture's bibliography (latex/ca-refs.bib).
% Book: extreport, every lecture is a chapter «Лекция N» (theorems are numbered
% <lecture>.<section>.<k>), one bibliography at the end (\printcoursebibliography).
%
%   \checkyourself{...}       — inline question, collected per lecture
%   \checkyourselfsection     — section listing the lecture's questions
%   \taskexample{<name>}      — \input{examples/<name>} (taskgen worked example)
% Labels must be unique within a semester: prefix them with the lecture
% number (\label{l3:euclid}); worked examples are labelled ex:<name>.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ca-notes}[2026/10/13 Computer Algebra lecture notes]

\newif\ifca@book \ca@bookfalse
\DeclareOption{book}{\ca@booktrue}
\DeclareOption*{%
  \PassOptionsToClass{\CurrentOption}{extarticle}%
  \PassOptionsToClass{\CurrentOption}{extreport}}
\PassOptionsToClass{12pt,a4paper}{extarticle}
\PassOptionsToClass{12pt,a4paper,openany}{extreport}
\ProcessOptions\relax
\ifca@book \LoadClass{extreport} \else \LoadClass{extarticle} \fi

\RequirePackage{ca-common}
\RequirePackage[a4paper,width=165mm,top=22mm,bottom=25mm,headheight=15pt]{geometry}
\RequirePackage{fancyhdr}
\RequirePackage{ca-figures}
\RequirePackage{ca-biblio}
\RequirePackage[hidelinks]{hyperref}
\RequirePackage{bookmark}
\ifca@book \RequirePackage{import} \fi
\setlength{\emergencystretch}{2em}

\newcommand{\coursename}{Компьютерная алгебра}
\newcounter{calecture}
\newcommand{\ca@lecnum}{??}
\newcommand{\ca@lectitle}{Без названия}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\textcolor{caGray}{\coursename}}
\fancyhead[R]{\small\textcolor{caGray}{\ifx\ca@lecnum\@empty\else Лекция~\ca@lecnum\fi}}
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

% --- one lecture ------------------------------------------------------------------------
\ifca@book
  \addto\captionsrussian{\renewcommand{\chaptername}{Лекция}}
  \renewcommand{\chaptername}{Лекция}
  \fancypagestyle{plain}{\fancyhf{}\fancyfoot[C]{\thepage}\renewcommand{\headrulewidth}{0pt}}
\fi
\newenvironment{lecture}[2]{%
  \setcounter{calecture}{#1}%
  \gdef\ca@lecnum{#1}\gdef\ca@lectitle{#2}\gdef\ca@cyqprefix{#1.}%
  \ca@resetcheckyourself
  \ifca@book
    \setcounter{chapter}{\numexpr#1-1\relax}%
    \chapter{#2}%
  \else
    \makelecturetitle
    \tableofcontents
  \fi
}{\par}

\newcommand{\checkyourselfsection}{%
  \section*{Вопросы для самопроверки}
  \addcontentsline{toc}{section}{Вопросы для самопроверки}
  \printcheckyourself
}

% Annotated reading list (\readitem / \item); standalone notes print the
% lecture's bibliography right after it.
\newenvironment{furtherreading}{%
  \section*{Литература и дополнительные материалы}
  \addcontentsline{toc}{section}{Литература и дополнительные материалы}
  \begin{itemize}%
}{%
  \end{itemize}%
  \ifca@book\else\printcabibliography\fi
}

\newcommand{\taskexample}[1]{\input{examples/#1}}

% --- the semester book ------------------------------------------------------------------
\newcommand{\ca@booksem}{??}
\newcommand{\ca@booktitle}{}
\newcommand{\coursebook}[2]{\renewcommand{\ca@booksem}{#1}\renewcommand{\ca@booktitle}{#2}}
\newcommand{\makebooktitle}{%
  \begin{titlepage}
    \centering\vspace*{0.25\textheight}
    {\Large\textcolor{caGray}{\coursename}\par}\bigskip
    {\Huge\bfseries Конспект лекций\par}\medskip
    {\LARGE Семестр~\ca@booksem\par}\bigskip
    \textcolor{caBlue}{\rule{0.6\linewidth}{0.8pt}}\par\bigskip
    {\Large\ca@booktitle\par}
    \vfill
  \end{titlepage}
  \gdef\ca@lecnum{}%
  \tableofcontents
}
\newcommand{\printcoursebibliography}{%
  \gdef\ca@lecnum{}%
  \cleardoublepage
  \phantomsection\addcontentsline{toc}{chapter}{Литература}%
  \chapter*{Литература}%
  \printcabibliography
}

\endinput
