/**
 * API 请求封装
 * 统一处理 Token、错误、响应结构
 */

// 前端由后端静态托管，使用同源相对路径，避免跨域问题
// 若要独立部署前端，可改为 'http://localhost:8080/api'
const API_BASE = '/api';

function getToken() {
    return localStorage.getItem('sgs_token');
}

function setToken(token) {
    localStorage.setItem('sgs_token', token);
}

function clearToken() {
    localStorage.removeItem('sgs_token');
    localStorage.removeItem('sgs_user');
}

function saveUser(user) {
    localStorage.setItem('sgs_user', JSON.stringify(user));
}

function getUser() {
    const s = localStorage.getItem('sgs_user');
    return s ? JSON.parse(s) : null;
}

/**
 * 通用请求方法
 */
async function request(path, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };

    const token = getToken();
    if (token) {
        headers['Authorization'] = 'Bearer ' + token;
    }

    const resp = await fetch(API_BASE + path, {
        ...options,
        headers
    });

    let body;
    try {
        body = await resp.json();
    } catch (e) {
        throw new Error('服务器响应格式错误');
    }

    if (!resp.ok || (body.code && body.code !== 200)) {
        if (body.code === 401) {
            clearToken();
            window.location.reload();
            throw new Error('登录已过期，请重新登录');
        }
        throw new Error(body.message || '请求失败');
    }

    return body.data;
}

const API = {
    // ---------- 认证 ----------
    login: (username, password) =>
        request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        }),

    logout: () => request('/auth/logout', { method: 'POST' }),

    me: () => request('/auth/me'),

    changePassword: (oldPassword, newPassword) =>
        request('/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({ oldPassword, newPassword })
        }),

    // ---------- 成绩 ----------
    listScores: (semester) =>
        request('/scores' + (semester ? '?semester=' + encodeURIComponent(semester) : '')),

    saveScore: (data) =>
        request('/scores', { method: 'POST', body: JSON.stringify(data) }),

    listScoreLogs: () => request('/scores/logs'),

    // ---------- 统计 ----------
    distribution: (semester) =>
        request('/stats/distribution' + (semester ? '?semester=' + encodeURIComponent(semester) : '')),

    courseAverage: (semester) =>
        request('/stats/course-average' + (semester ? '?semester=' + encodeURIComponent(semester) : '')),

    classAverage: (semester) =>
        request('/stats/class-average' + (semester ? '?semester=' + encodeURIComponent(semester) : '')),

    passRate: (semester) =>
        request('/stats/pass-rate' + (semester ? '?semester=' + encodeURIComponent(semester) : '')),

    studentTrend: (studentId) => request('/stats/student-trend/' + studentId),

    semesters: () => request('/stats/semesters'),

    // ---------- 基础信息 ----------
    listStudents: () => request('/basic/students'),
    addStudent: (data) => request('/basic/students', { method: 'POST', body: JSON.stringify(data) }),
    deleteStudent: (id) => request('/basic/students/' + id, { method: 'DELETE' }),

    listTeachers: () => request('/basic/teachers'),
    addTeacher: (data) => request('/basic/teachers', { method: 'POST', body: JSON.stringify(data) }),

    listCourses: () => request('/basic/courses'),
    addCourse: (data) => request('/basic/courses', { method: 'POST', body: JSON.stringify(data) }),
    deleteCourse: (id) => request('/basic/courses/' + id, { method: 'DELETE' }),

    listClasses: () => request('/basic/classes')
};
