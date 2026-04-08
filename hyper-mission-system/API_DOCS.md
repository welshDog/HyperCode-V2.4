# Hyper-Mission API Documentation

## Base URL
`https://localhost/api`

## Authentication
Currently open (Internal use). Rate limiting is applied (100 requests / 10 mins).

## Endpoints

### 1. Tasks

#### Get All Tasks
- **URL**: `/tasks`
- **Method**: `GET`
- **Description**: Retrieves all tasks sorted by priority score.
- **Response**: `200 OK`
  ```json
  [
    {
      "id": 1,
      "title": "Task 1",
      "priority_score": 10.5,
      ...
    }
  ]
  ```

#### Create Task
- **URL**: `/tasks`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "title": "New Feature",
    "description": "Implement X",
    "impact": 5,
    "effort": 3,
    "urgency": "high",
    "due_date": "2023-12-31"
  }
  ```
- **Response**: `201 Created`

#### Breakdown Task
- **URL**: `/tasks/:id/breakdown`
- **Method**: `POST`
- **Description**: Uses AI (Mock) to break a task into subtasks.
- **Response**: `201 Created` (Array of subtasks)

#### Mark Task as Done
- **URL**: `/tasks/:id/done`
- **Method**: `PUT`
- **Description**: Marks a task as completed. Requires evidence and peer review.
- **Body**:
  ```json
  {
    "evidence_link": "http://github.com/pr/123",
    "peer_review_checked": true
  }
  ```
- **Response**: `200 OK`

### 2. Dashboard

#### Get Dashboard Stats
- **URL**: `/dashboard`
- **Method**: `GET`
- **Response**: `200 OK`
  ```json
  {
    "percent_complete": 45,
    "velocity_trend": "stable",
    "next_action": "Review...",
    "blockers": 0
  }
  ```

### 3. Standup

#### Generate Standup Report
- **URL**: `/standup`
- **Method**: `GET`
- **Description**: Generates a daily standup summary based on task activity.
- **Response**: `200 OK`
  ```json
  {
    "yesterday": ["Task A", "Task B"],
    "today": ["Task C"],
    "impediments": ["None"]
  }
  ```
