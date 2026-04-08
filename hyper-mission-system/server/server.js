const express = require('express');
const cors = require('cors');
const morgan = require('morgan');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const xss = require('xss-clean');
const hpp = require('hpp');
const compression = require('compression');
const { Pool } = require('pg');
const client = require('prom-client');
const redis = require('redis');
const jwt = require('jsonwebtoken');
const authenticate = require('./middleware/auth');
require('dotenv').config();

const app = express();
const port = process.env.PORT || 5000;

const redisClient = process.env.NODE_ENV === 'test'
  ? {
    get: async () => null,
    setEx: async () => null,
    connect: async () => null,
  }
  : redis.createClient({ url: process.env.REDIS_URL || 'redis://redis:6379' });
redisClient.connect().catch(console.error);

// Cache Middleware
const cacheMiddleware = (duration) => async (req, res, next) => {
  const key = `cache:${req.originalUrl}`;
  try {
    const cached = await redisClient.get(key);
    if (cached) {
      return res.json(JSON.parse(cached));
    }
    
    const originalJson = res.json.bind(res);
    res.json = (data) => {
      redisClient.setEx(key, duration, JSON.stringify(data));
      return originalJson(data);
    };
    next();
  } catch (err) {
    console.error('Redis Error:', err);
    next();
  }
};

// Prometheus Metrics
const register = new client.Registry();
client.collectDefaultMetrics({ register });

// Custom Metrics
const taskCounter = new client.Counter({
  name: 'task_operations_total',
  help: 'Total number of task operations',
  labelNames: ['operation', 'status'],
  registers: [register]
});

const taskDuration = new client.Histogram({
  name: 'task_duration_seconds',
  help: 'Duration of task operations in seconds',
  labelNames: ['operation'],
  registers: [register]
});

// Metrics Endpoint
app.get('/metrics', async (req, res) => {
  res.setHeader('Content-Type', register.contentType);
  res.send(await register.metrics());
});

// Security & Optimization Middleware
app.use(helmet()); // Set security headers
app.use(xss()); // Prevent XSS attacks
app.use(hpp()); // Prevent HTTP Parameter Pollution
app.use(compression()); // Compress responses

// Rate Limiting
const limiter = rateLimit({
  windowMs: 10 * 60 * 1000, // 10 mins
  max: 100 // limit each IP to 100 requests per windowMs
});
app.use('/api', limiter);

// Standard Middleware
app.use(cors());
app.use(express.json({ limit: '10kb' })); // Body limit
app.use(morgan('dev'));

// Database
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

const coreBaseUrl = process.env.CORE_API_URL || null;
const useCore = Boolean(coreBaseUrl);
const projectIdCache = new Map();

// Priority Matrix Logic
const calculatePriority = (impact, effort, urgency) => {
  const urgencyScores = { 'critical': 1.5, 'high': 1.2, 'medium': 1.0, 'low': 0.8 };
  return (impact * urgencyScores[urgency]) / effort;
};

const mapCoreTaskToMissionTask = (t) => {
  const priority = String(t.priority || 'medium').toLowerCase();
  const urgency = priority === 'high' ? 'critical' : priority === 'low' ? 'low' : 'medium';
  const impact = priority === 'high' ? 8 : priority === 'low' ? 3 : 5;
  const effort = 3;
  const status = String(t.status || 'todo').toLowerCase() === 'done' ? 'completed' : 'pending';
  return {
    id: t.id,
    title: t.title,
    description: t.description,
    status,
    impact,
    effort,
    urgency,
    due_date: null,
  };
};

const coreRequest = async (path, { method = 'GET', authHeader, jsonBody } = {}) => {
  if (!coreBaseUrl) {
    throw new Error('CORE_API_URL is not configured');
  }
  const headers = {};
  if (authHeader) {
    headers.Authorization = authHeader;
  }
  if (jsonBody !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  const resp = await fetch(`${coreBaseUrl}${path}`, {
    method,
    headers,
    body: jsonBody !== undefined ? JSON.stringify(jsonBody) : undefined,
  });
  const text = await resp.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch (e) {
    data = text;
  }
  return { status: resp.status, ok: resp.ok, data };
};

const getDefaultProjectId = async (authHeader) => {
  if (projectIdCache.has(authHeader)) {
    return projectIdCache.get(authHeader);
  }
  const resp = await coreRequest('/projects/', { method: 'GET', authHeader });
  if (!resp.ok || !Array.isArray(resp.data) || resp.data.length === 0) {
    throw new Error('No projects available');
  }
  const projectId = resp.data[0].id;
  projectIdCache.set(authHeader, projectId);
  return projectId;
};

// Routes

// Auth Routes
app.post('/api/auth/login', async (req, res) => {
  const { username, password } = req.body;
  if (useCore) {
    try {
      const params = new URLSearchParams();
      params.set('username', username);
      params.set('password', password);
      const resp = await fetch(`${coreBaseUrl}/auth/login/access-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params.toString(),
      });
      const payload = await resp.text();
      let data = null;
      try {
        data = payload ? JSON.parse(payload) : null;
      } catch (e) {
        data = payload;
      }
      if (!resp.ok) {
        return res.status(resp.status).json(typeof data === 'string' ? { error: data } : data);
      }
      return res.json({ token: data.access_token });
    } catch (err) {
      return res.status(502).json({ error: 'Core API login failed' });
    }
  }

  if (username === 'admin' && password === 'admin') {
    const token = jwt.sign({ username: 'admin', role: 'admin' }, process.env.JWT_SECRET, { expiresIn: '1h' });
    return res.json({ token });
  }

  return res.status(401).json({ error: 'Invalid credentials' });
});

// Protect all API routes below
app.use('/api', authenticate);

// Get all tasks (with optional sorting)
app.get('/api/tasks', async (req, res) => {
  if (useCore) {
    try {
      const authHeader = req.headers.authorization;
      const coreResp = await coreRequest('/tasks/?skip=0&limit=200', { method: 'GET', authHeader });
      if (!coreResp.ok) {
        return res.status(coreResp.status).json(coreResp.data || { error: 'Core API error' });
      }
      const tasks = (coreResp.data || []).map(mapCoreTaskToMissionTask).map(task => ({
        ...task,
        priority_score: calculatePriority(task.impact, task.effort, task.urgency)
      }));
      tasks.sort((a, b) => b.priority_score - a.priority_score);
      return res.json(tasks);
    } catch (err) {
      return res.status(500).json({ error: 'Server error' });
    }
  }
  try {
    const result = await pool.query('SELECT * FROM tasks');
    // Sort by weighted priority in memory for now or move logic to SQL
    const tasks = result.rows.map(task => ({
      ...task,
      priority_score: calculatePriority(task.impact, task.effort, task.urgency)
    }));
    tasks.sort((a, b) => b.priority_score - a.priority_score);
    res.json(tasks);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Server error' });
  }
});

// Create Task
app.post('/api/tasks', async (req, res) => {
  const end = taskDuration.startTimer({ operation: 'create_task' });
  const { title, description, impact, effort, urgency, due_date } = req.body;
  try {
    if (useCore) {
      const authHeader = req.headers.authorization;
      const projectId = req.body.project_id || await getDefaultProjectId(authHeader);
      const corePriority = urgency === 'critical' || impact >= 8 ? 'high' : impact <= 3 ? 'low' : 'medium';
      const coreResp = await coreRequest('/tasks/', {
        method: 'POST',
        authHeader,
        jsonBody: {
          title,
          description,
          priority: corePriority,
          project_id: projectId,
          type: 'mission',
        }
      });
      if (!coreResp.ok) {
        taskCounter.inc({ operation: 'create_task', status: 'error' });
        end();
        return res.status(coreResp.status).json(coreResp.data || { error: 'Core API error' });
      }
      taskCounter.inc({ operation: 'create_task', status: 'success' });
      end();
      return res.status(201).json(mapCoreTaskToMissionTask(coreResp.data));
    }

    const result = await pool.query(
      'INSERT INTO tasks (title, description, impact, effort, urgency, due_date, status) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *',
      [title, description, impact, effort, urgency, due_date, 'pending']
    );
    taskCounter.inc({ operation: 'create_task', status: 'success' });
    end();
    res.status(201).json(result.rows[0]);
  } catch (err) {
    taskCounter.inc({ operation: 'create_task', status: 'error' });
    end();
    console.error(err);
    res.status(500).json({ error: 'Server error' });
  }
});

// Breakdown Task (Mock Engine)
app.post('/api/tasks/:id/breakdown', async (req, res) => {
  const { id } = req.params;
  try {
    if (useCore) {
      const authHeader = req.headers.authorization;
      const parentResp = await coreRequest(`/tasks/${id}`, { method: 'GET', authHeader });
      if (!parentResp.ok) {
        return res.status(parentResp.status).json(parentResp.data || { error: 'Task not found' });
      }
      const parent = parentResp.data;
      const subtasks = [
        { id: `${id}-1`, title: `Research ${parent.title}`, duration_minutes: 15, is_done: false },
        { id: `${id}-2`, title: `Draft outline for ${parent.title}`, duration_minutes: 15, is_done: false },
        { id: `${id}-3`, title: 'Review requirements', duration_minutes: 15, is_done: false },
      ];
      return res.status(201).json(subtasks);
    }

    // 1. Fetch parent task
    const parent = await pool.query('SELECT * FROM tasks WHERE id = $1', [id]);
    if (parent.rows.length === 0) return res.status(404).json({ error: 'Task not found' });
    
    // 2. Mock Breakdown Logic (would be LLM)
    const subtasks = [
      { title: `Research ${parent.rows[0].title}`, duration: 15 },
      { title: `Draft outline for ${parent.rows[0].title}`, duration: 15 },
      { title: `Review requirements`, duration: 15 }
    ];
    
    // 3. Insert subtasks
    const createdSubtasks = [];
    for (const st of subtasks) {
      const result = await pool.query(
        'INSERT INTO subtasks (parent_id, title, duration_minutes, is_done) VALUES ($1, $2, $3, $4) RETURNING *',
        [id, st.title, st.duration, false]
      );
      createdSubtasks.push(result.rows[0]);
    }
    
    res.status(201).json(createdSubtasks);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Server error' });
  }
});

// Mark Done (with validation)
app.put('/api/tasks/:id/done', async (req, res) => {
  const { id } = req.params;
  const { evidence_link, peer_review_checked } = req.body;
  
  if (!evidence_link || !peer_review_checked) {
    return res.status(400).json({ error: 'Done Definition not met: Missing evidence or peer review.' });
  }
  
  try {
    if (useCore) {
      const authHeader = req.headers.authorization;
      const taskResp = await coreRequest(`/tasks/${id}`, { method: 'GET', authHeader });
      if (!taskResp.ok) {
        return res.status(taskResp.status).json(taskResp.data || { error: 'Task not found' });
      }
      const existingOutput = taskResp.data.output || '';
      const evidenceBlock = `\n\n## Evidence\n- Link: ${evidence_link}\n- Peer reviewed: ${peer_review_checked ? 'yes' : 'no'}\n`;
      const updatedOutput = `${existingOutput}${evidenceBlock}`.trim();
      const updateResp = await coreRequest(`/tasks/${id}`, {
        method: 'PUT',
        authHeader,
        jsonBody: { status: 'done', output: updatedOutput }
      });
      if (!updateResp.ok) {
        return res.status(updateResp.status).json(updateResp.data || { error: 'Core API error' });
      }
      return res.json(mapCoreTaskToMissionTask(updateResp.data));
    }

    const result = await pool.query(
      'UPDATE tasks SET status = $1, evidence_link = $2 WHERE id = $3 RETURNING *',
      ['completed', evidence_link, id]
    );
    if (result.rows.length === 0) return res.status(404).json({ error: 'Task not found' });
    res.json(result.rows[0]);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Server error' });
  }
});

// Dashboard Stats
app.get('/api/dashboard', cacheMiddleware(60), async (req, res) => {
  try {
    if (useCore) {
      const authHeader = req.headers.authorization;
      const tasksResp = await coreRequest('/tasks/?skip=0&limit=500', { method: 'GET', authHeader });
      if (!tasksResp.ok) {
        return res.status(tasksResp.status).json(tasksResp.data || { error: 'Core API error' });
      }
      const tasks = tasksResp.data || [];
      const total = tasks.length;
      const done = tasks.filter(t => String(t.status || '').toLowerCase() === 'done').length;
      const percentComplete = total ? (done / total) * 100 : 0;
      return res.json({
        percent_complete: percentComplete,
        velocity_trend: 'stable',
        next_action: 'Review pending high-priority items',
        blockers: 0
      });
    }

    const total = await pool.query('SELECT COUNT(*) FROM tasks');
    const completed = await pool.query("SELECT COUNT(*) FROM tasks WHERE status = 'completed'");
    const velocity = 5; // Mock velocity
    
    res.json({
      percent_complete: (parseInt(completed.rows[0].count) / parseInt(total.rows[0].count)) * 100 || 0,
      velocity_trend: 'stable',
      next_action: 'Review pending high-priority items',
      blockers: 0
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Server error' });
  }
});

// Standup Generator
app.get('/api/standup', async (req, res) => {
  try {
    if (useCore) {
      const authHeader = req.headers.authorization;
      const tasksResp = await coreRequest('/tasks/?skip=0&limit=500', { method: 'GET', authHeader });
      if (!tasksResp.ok) {
        return res.status(tasksResp.status).json(tasksResp.data || { error: 'Core API error' });
      }
      const now = Date.now();
      const yesterdayCutoff = now - 24 * 60 * 60 * 1000;
      const doneYesterday = [];
      const today = [];
      for (const t of tasksResp.data || []) {
        const status = String(t.status || '').toLowerCase();
        const updatedAt = t.updated_at ? Date.parse(t.updated_at) : null;
        if (status === 'done' && updatedAt && updatedAt < yesterdayCutoff) {
          doneYesterday.push(t.title);
        }
        if (status !== 'done' && today.length < 3) {
          today.push(t.title);
        }
      }
      const summary = { yesterday: doneYesterday, today, impediments: ['None'] };
      return res.json(summary);
    }

    const yesterday = await pool.query("SELECT title FROM tasks WHERE status = 'completed' AND due_date < NOW()");
    const today = await pool.query("SELECT title FROM tasks WHERE status = 'pending' LIMIT 3");
    
    const summary = {
      yesterday: yesterday.rows.map(t => t.title),
      today: today.rows.map(t => t.title),
      impediments: ["None"]
    };
    // Mock email sending
    console.log("Sending email:", summary);
    res.json(summary);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Server error' });
  }
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

if (require.main === module) {
  app.listen(port, () => {
    console.log(`Server running on port ${port}`);
  });
}

module.exports = app; // For testing
