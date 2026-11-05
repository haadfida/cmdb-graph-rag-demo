# Recording the demo GIF

1. Copy `.env.example` to `.env` and set `GOOGLE_API_KEY`.
2. Run `docker compose up` and wait for Neo4j to report healthy and the frontend at http://localhost:5173.
3. Load data if needed (see README), then ask these questions in the UI, waiting for each answer and graph:
   - "What services break if DB-Server goes down?"
   - "Who owns Payroll-Service?"
   - "Show everything in Data-Center-1"
4. Save as `docs/demo.gif` (aim for under 10 MB, ~1000px wide, 10-15 fps).

## The recording should capture
- `docker compose up` finishing and the UI loading
- Each question typed in the input box
- The generated answer text for each question
- The graph visualization updating with the relevant nodes and edges
- Hovering or clicking a node to show its details (optional)
- Total length about 30-60 seconds
