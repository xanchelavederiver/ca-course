# Computer Algebra course project

This repo is Computer Algebra (or rather, introduction to Mathematical Cryptography) course project.
The purpose of this project is to produce lecture slides and notes, generate task sheets for seminars and homeworks, exam questions sheets and other course materials.

The course structure is:

- 2 semesters
- зачёт after the first semester, final exam after the second semester


## Course materials

- lecture slides
- lecture notes
- seminar handouts and classroom task sheets
- homework/exam task sheets (assignments)
- [capstone] project
- exam questions

### Lecture slides

The lecture slides are essentially canvases with the basic definitions/theorems; the proofs and additional info will be written on top of the slides.
Therefore the system must be capable of handling LaTeX and smth. like Cintiq with pen.

Slides are LaTeX Beamer documents compiled to PDF (annotated live with a pen); the existing PPTX decks are ported to Beamer over time.
HTML export is optional and may be added later.

See `tmp/лекции` for two example lecture slides.

### Lecture notes

Lecture notes are math-heavy PDF files to be handed the students as the prime source of information regarding the respective lecture's topics.

Every lecture note contains:

- the basic info plus additional topics - theorems, lemmas, corollaries, propositions, examples
- check yourself questions scattered around the document and a dedicated section towards the end of the notes
- references and additional readings / video lectures / MOOCs / etc.

The source files for the lecture notes are LaTex files.

### Seminar handouts and classroom task sheets, homework/exam task sheets

Seminar handouts are short PDFs that are necessary to briefly remind students the relevant theory - 1-2 pages at most.
The handouts are LaTex sources build similarly to the lecture notes.

The classroom task sheets are composed of several groups of tasks dedicated to one topic. These tasks are to be solved on seminar.
The task sheets project (see below) must generate both the task sheet and the tasks solution that contains the same tasks along with the detailed solutions.

The homework/exam task sheets are analogous to the classroom task sheets with a vital distinction: these are to be generated in multiple variants - every student gets an individual variant.

See `tmp/практики и контрольные` for examples of Python scripts that generate exam task sheets.

### [capstone] project

An optional project (курсовая) - a student is asked to implement an algorithm (e.g. Pohlig-Hellman in Z/nZ).
The tasks are given in the form of a PDF file - project's specification.

This course project should contain reference solution implementations (dockerized) to experimentally estimate the requirements.

See `tmp/курсовые` for examples of the capstone projects specs.

### Exam questions

A couple of exam questions (зачёт and экзамен, respectively) - LaTeX source files built to PDF text files.
Each exam questions sheet has an accompanying version with references.

See `tmp/вопросы на экзамен` for examples of the exam questions pairs.


## Task sheets project

The project is expected to generate various task sheets and corresponding solution manuals with detailed step-by-step solutions.

The project operates on a database of the tasks and each task sheet is described as a set of selected tasks.

Tasks can be fully-defined or templates which can be instantiated by substituting random numbers as input values - this way a task template can be used 
to generate multiple variants of essentially the same task with different values (to be used in the individual task sheets).
Tasks are also tagged by the topics they cover and by their complexity.

The classroom task sheets are well-defined sets of tasks that are chosen to help students digest the material and draw their attention to particular corner cases - 
therefore, although these task sheets can have randomized tasks, there is a single sheet produced for each seminar.

Homework task sheets (домашняя контрольная, листочки) are generated as individual student tasks. These sheets are composed of sets of projects identified by the topic and complexity.
Each sheet has total complexity budget which is spent on task of varying complexity - this is a way of randomizing the variants even more.
Exam task sheets are essentially the same but cover more topics.

The task sheets project generates LaTeX files that are then used to generate PDF files.

Requirements for generation:

- deterministic, seeded generation: every issued sheet (classroom or individual variants) is archived together with its answer key,
  the master seed, a snapshot of the sheet definition, the generator version and the git commit, so that any variant can be reproduced and verified later;
- per-instance validation: each generated task instance is self-checked (the solution is verified, the values are within sane bounds) before it is put on a sheet.

The desired UI - a web application that allows to:

- create/edit tasks (templates, tags, values generation rules, etc.)
- create/edit task sheets (with individual variants or just a single instance)
- generate LaTeX and PDF files
- preview the results


## Misc

The build system is expected to use docker containers and produce ready artifacts: PDF files (HTML/PPTX export optional, later).

## Non-goals

- no student portal: materials are distributed by the instructor;
- no grading system: the project produces sheets and answer keys, grading happens elsewhere;
- single-instructor tool: no multi-user accounts or permissions.
