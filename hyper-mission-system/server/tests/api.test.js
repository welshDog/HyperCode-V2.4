const request = require('supertest');

process.env.NODE_ENV = 'test';
process.env.AUTH_PASSTHROUGH = 'true';
process.env.JWT_SECRET = 'test-secret';
delete process.env.CORE_API_URL;

const app = require('../server');
const { Pool } = require('pg');

// Mock PG Pool
jest.mock('pg', () => {
  const mPool = {
    query: jest.fn(),
  };
  return { Pool: jest.fn(() => mPool) };
});

describe('Hyper-Mission API', () => {
  let pool;
  const authHeader = { Authorization: 'Bearer test' };

  beforeEach(() => {
    pool = new (require('pg').Pool)();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  // --- GET /api/tasks ---
  it('GET /api/tasks returns sorted tasks', async () => {
    const mockTasks = [
      { id: 1, title: 'Task 1', impact: 5, effort: 5, urgency: 'medium' },
      { id: 2, title: 'Task 2', impact: 10, effort: 2, urgency: 'critical' }
    ];
    pool.query.mockResolvedValueOnce({ rows: mockTasks });

    const res = await request(app).get('/api/tasks').set(authHeader);
    
    expect(res.statusCode).toEqual(200);
    expect(res.body.length).toEqual(2);
    // Task 2 should be first (Score: 10*1.5/2 = 7.5 vs 5*1.0/5 = 1.0)
    expect(res.body[0].title).toEqual('Task 2');
  });

  it('GET /api/tasks handles errors', async () => {
    pool.query.mockRejectedValueOnce(new Error('DB Error'));
    const res = await request(app).get('/api/tasks').set(authHeader);
    expect(res.statusCode).toEqual(500);
  });

  // --- POST /api/tasks ---
  it('POST /api/tasks creates a task', async () => {
    const newTask = { title: 'New', impact: 5, effort: 5, urgency: 'medium' };
    pool.query.mockResolvedValueOnce({ rows: [{ id: 3, ...newTask, status: 'pending' }] });

    const res = await request(app).post('/api/tasks').set(authHeader).send(newTask);
    
    expect(res.statusCode).toEqual(201);
    expect(res.body.id).toEqual(3);
  });

  it('POST /api/tasks handles errors', async () => {
    pool.query.mockRejectedValueOnce(new Error('DB Error'));
    const res = await request(app).post('/api/tasks').set(authHeader).send({});
    expect(res.statusCode).toEqual(500);
  });

  // --- PUT /api/tasks/:id/done ---
  it('PUT /api/tasks/:id/done validates done definition', async () => {
    const res = await request(app).put('/api/tasks/1/done').set(authHeader).send({});
    expect(res.statusCode).toEqual(400);
    expect(res.body.error).toContain('Done Definition not met');
  });

  it('PUT /api/tasks/:id/done succeeds with evidence', async () => {
    pool.query.mockResolvedValueOnce({ rows: [{ id: 1, status: 'completed' }] });
    const res = await request(app).put('/api/tasks/1/done').set(authHeader).send({
      evidence_link: 'http://github.com',
      peer_review_checked: true
    });
    expect(res.statusCode).toEqual(200);
    expect(res.body.status).toEqual('completed');
  });

  it('PUT /api/tasks/:id/done handles not found', async () => {
    pool.query.mockResolvedValueOnce({ rows: [] });
    const res = await request(app).put('/api/tasks/999/done').set(authHeader).send({
        evidence_link: 'http://github.com',
        peer_review_checked: true
    });
    expect(res.statusCode).toEqual(404);
  });

  it('PUT /api/tasks/:id/done handles errors', async () => {
      pool.query.mockRejectedValueOnce(new Error('DB Error'));
      const res = await request(app).put('/api/tasks/1/done').set(authHeader).send({
          evidence_link: 'http://github.com',
          peer_review_checked: true
      });
      expect(res.statusCode).toEqual(500);
  });

  // --- POST /api/tasks/:id/breakdown ---
  it('POST /api/tasks/:id/breakdown creates subtasks', async () => {
    // Mock fetching parent task
    pool.query.mockResolvedValueOnce({ rows: [{ id: 1, title: 'Parent Task' }] });
    // Mock inserting subtasks (called 3 times in loop)
    pool.query
      .mockResolvedValueOnce({ rows: [{ id: 101, title: 'Research Parent Task' }] })
      .mockResolvedValueOnce({ rows: [{ id: 102, title: 'Draft outline' }] })
      .mockResolvedValueOnce({ rows: [{ id: 103, title: 'Review requirements' }] });

    const res = await request(app).post('/api/tasks/1/breakdown').set(authHeader);
    expect(res.statusCode).toEqual(201);
    expect(res.body.length).toEqual(3);
  });

  it('POST /api/tasks/:id/breakdown handles parent not found', async () => {
    pool.query.mockResolvedValueOnce({ rows: [] });
    const res = await request(app).post('/api/tasks/999/breakdown').set(authHeader);
    expect(res.statusCode).toEqual(404);
  });

  it('POST /api/tasks/:id/breakdown handles errors', async () => {
      pool.query.mockRejectedValueOnce(new Error('DB Error'));
      const res = await request(app).post('/api/tasks/1/breakdown').set(authHeader);
      expect(res.statusCode).toEqual(500);
  });

  // --- GET /api/dashboard ---
  it('GET /api/dashboard returns stats', async () => {
    pool.query
      .mockResolvedValueOnce({ rows: [{ count: '10' }] }) // Total
      .mockResolvedValueOnce({ rows: [{ count: '5' }] }); // Completed

    const res = await request(app).get('/api/dashboard').set(authHeader);
    expect(res.statusCode).toEqual(200);
    expect(res.body.percent_complete).toEqual(50);
    expect(res.body.velocity_trend).toEqual('stable');
  });

  it('GET /api/dashboard handles errors', async () => {
      pool.query.mockRejectedValueOnce(new Error('DB Error'));
      const res = await request(app).get('/api/dashboard').set(authHeader);
      expect(res.statusCode).toEqual(500);
  });

  // --- GET /api/standup ---
  it('GET /api/standup returns summary', async () => {
    pool.query
      .mockResolvedValueOnce({ rows: [{ title: 'Task A' }] }) // Yesterday
      .mockResolvedValueOnce({ rows: [{ title: 'Task B' }] }); // Today

    const res = await request(app).get('/api/standup').set(authHeader);
    expect(res.statusCode).toEqual(200);
    expect(res.body.yesterday).toContain('Task A');
    expect(res.body.today).toContain('Task B');
  });

  it('GET /api/standup handles errors', async () => {
      pool.query.mockRejectedValueOnce(new Error('DB Error'));
      const res = await request(app).get('/api/standup').set(authHeader);
      expect(res.statusCode).toEqual(500);
  });

});
