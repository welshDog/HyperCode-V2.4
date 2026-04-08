# Hyper-Mission Control System

A high-performance mission management system with hierarchical breakdowns, priority matrix, and done validation.

## 🚀 Quick Start

1.  **Prerequisites**: Docker & Docker Compose.
2.  **Navigate**: `cd hyper-mission-system`
3.  **Start**: `docker-compose up --build`
4.  **Access**:
    *   Frontend: [http://localhost:5173](http://localhost:5173)
    *   API: [http://localhost:5000](http://localhost:5000)
5.  **Seed Data**: The database is automatically seeded with 20 rows on first run.

## 🛠 Tech Stack

*   **Frontend**: React (Vite), TailwindCSS, Lucide Icons
*   **Backend**: Node.js, Express
*   **Database**: PostgreSQL
*   **Testing**: Jest, Supertest

## 🔑 Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | 5000 | API Port |
| `DATABASE_URL` | postgres://user:password@postgres:5432/hypermission | DB Connection |

## 🧪 Testing

Run unit tests with coverage:

```bash
cd server
npm install
npm test
```

## 📦 Features

*   **Priority Matrix**: Auto-sorts tasks by (Impact * Urgency) / Effort.
*   **Done Validator**: Enforces evidence links and peer reviews.
*   **Standup Generator**: One-click daily report.
*   **Task Breakdown**: Auto-decomposes tasks (mock engine).

