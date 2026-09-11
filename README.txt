ARCHFLOW — PROJECT COMMUNICATION INTELLIGENCE
AS-02 · Communication

Turn project conversations into project actions.

FEATURES
- Communication analysis for project messages
- Automatic summary, risks, decisions and action items
- Deadline detection and action linking
- Project health and priority assessment
- Drawing revision conflict detection
- Material availability and material replacement detection
- Project-memory change detection
- Persistent SQLite history and action status tracking
- Multiple demo scenarios
- Dedicated Project Intelligence result page after analysis
- Persistent project history
- Printable/exportable project report

TECH STACK
Python, Flask, HTML, CSS, JavaScript, SQLite

RUN LOCALLY
1. Open PowerShell in this folder.
2. Run: python app.py
3. Open: http://127.0.0.1:5000

NOTES
- The project does not require a paid API or external AI service.
- archflow.db is created automatically when the application starts.
- Do not copy a virtual environment from another machine.
- For a clean submission, exclude venv, __pycache__, and archflow.db unless sample history is specifically required.

DEMO FLOW
1. Open the Communication Inbox and load Material Shortage.
2. Click Analyze Communication to open the dedicated Project Intelligence page.
3. Load Revision Conflict from the Communication page and analyze.
4. Load Project Delay and analyze.
5. Load Material Change & Approval and show M-305 → M-310.
6. Load Healthy Project and show HEALTHY / LOW.
7. Change one action status and show that it persists.
8. Open Project History to revisit an analysis and Export Report.
