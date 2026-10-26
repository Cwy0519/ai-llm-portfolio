/**
 * 学生成绩管理系统  前端主逻辑
 */

let currentUser = null;
let charts = {};
let modalSubmitHandler = null;

// ============================================================
//  初始化
// ============================================================
window.addEventListener('DOMContentLoaded', async () => {
    // 支持通过 URL hash 携带令牌与目标页（用于自动化截图/调试）
    // 形如：http://localhost:8080/#token=xxxx&page=score
    const hash = location.hash;
    let targetPage = null;
    if (hash && hash.length > 1) {
        const params = new URLSearchParams(hash.substring(1));
        const t = params.get('token');
        targetPage = params.get('page');
        if (t) {
            setToken(t);
            try {
                const me = await API.me();
                saveUser({
                    userId: me.userId,
                    username: me.username,
                    realName: me.realName,
                    roles: me.roles,
                    permissions: me.permissions
                });
            } catch (e) { /* 令牌无效则走正常登录 */ }
        }
        history.replaceState(null, '', location.pathname);
    }

    const token = getToken();
    if (token && getUser()) {
        currentUser = getUser();
        enterMain(targetPage);
    } else {
        document.getElementById('loginPage').style.display = 'flex';
    }

    const form = document.getElementById('loginForm');
    if (form) form.addEventListener('submit', handleLogin);
});

function fillLogin(username) {
    document.getElementById('username').value = username;
    document.getElementById('password').value = '123456';
    document.getElementById('loginError').textContent = '';
}

// ============================================================
//  登录 / 登出
// ============================================================
async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const errEl = document.getElementById('loginError');
    errEl.textContent = '';

    try {
        const data = await API.login(username, password);
        setToken(data.token);
        saveUser({
            userId: data.userId,
            username: data.username,
            realName: data.realName,
            roles: data.roles,
            permissions: data.permissions
        });
        currentUser = getUser();
        enterMain();
        toast('登录成功，欢迎 ' + data.realName, 'success');
    } catch (err) {
        errEl.textContent = err.message;
    }
}

async function logout() {
    try {
        await API.logout();
    } catch (e) { /* 忽略 */ }
    clearToken();
    location.reload();
}

function enterMain(targetPage) {
    document.getElementById('loginPage').style.display = 'none';
    document.getElementById('mainPage').style.display = 'flex';

    document.getElementById('userName').textContent = currentUser.realName;
    const roleName = currentUser.roles.includes('ADMIN') ? '管理员'
        : currentUser.roles.includes('TEACHER') ? '教师' : '学生';
    document.getElementById('userRole').textContent = roleName;

    buildMenu();

    // 若指定了目标页面且菜单中存在，则跳转过去
    const validPages = ['dashboard', 'score', 'student', 'teacher', 'course', 'log'];
    if (targetPage && validPages.includes(targetPage)
        && document.querySelector(`.nav-item[data-page="${targetPage}"]`)) {
        switchPage(targetPage);
    } else {
        switchPage('dashboard');
    }
}

// ============================================================
//  菜单（按权限显示）
// ============================================================
function buildMenu() {
    const perms = currentUser.permissions || [];
    const isStudent = currentUser.roles.includes('STUDENT');

    const menu = [
        { id: 'dashboard', label: '仪表盘', icon: '📊', show: perms.includes('stats:view') },
        { id: 'score', label: isStudent ? '我的成绩' : '成绩管理', icon: '📝', show: perms.includes('score:view') },
        { id: 'student', label: '学生管理', icon: '👨‍🎓', show: perms.includes('student:view') && !isStudent },
        { id: 'teacher', label: '教师管理', icon: '👨‍🏫', show: perms.includes('teacher:view') && !isStudent },
        { id: 'course', label: '课程管理', icon: '📚', show: perms.includes('course:view') },
        { id: 'log', label: '审计日志', icon: '🔍', show: perms.includes('score:audit') }
    ];

    const nav = document.getElementById('navMenu');
    nav.innerHTML = '';
    menu.filter(m => m.show).forEach(m => {
        const div = document.createElement('div');
        div.className = 'nav-item';
        div.dataset.page = m.id;
        div.innerHTML = `<span>${m.icon}</span><span>${m.label}</span>`;
        div.onclick = () => switchPage(m.id);
        nav.appendChild(div);
    });
}

// ============================================================
//  页面切换
// ============================================================
function switchPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const page = document.getElementById('page-' + pageId);
    if (page) page.classList.add('active');

    const navItem = document.querySelector(`.nav-item[data-page="${pageId}"]`);
    if (navItem) navItem.classList.add('active');

    const titles = {
        dashboard: '仪表盘',
        score: currentUser.roles.includes('STUDENT') ? '我的成绩' : '成绩管理',
        student: '学生管理',
        teacher: '教师管理',
        course: '课程管理',
        log: '审计日志'
    };
    document.getElementById('pageTitle').textContent = titles[pageId] || '';

    // 延迟加载，确保容器已显示（ECharts 需要宽度）
    setTimeout(() => {
        if (pageId === 'dashboard') loadDashboard();
        if (pageId === 'score') loadScores();
        if (pageId === 'student') loadStudents();
        if (pageId === 'teacher') loadTeachers();
        if (pageId === 'course') loadCourses();
        if (pageId === 'log') loadLogs();
    }, 50);
}

// ============================================================
//  仪表盘 + ECharts
// ============================================================
async function loadDashboard() {
    try {
        const semester = document.getElementById('semesterFilter')?.value || '';

        const [dist, pass, courseAvg, classAvg] = await Promise.all([
            API.distribution(semester),
            API.passRate(semester),
            API.courseAverage(semester),
            API.classAverage(semester)
        ]);

        // 顶部统计卡片
        document.getElementById('statTotal').textContent = dist.total || 0;
        document.getElementById('statPassRate').textContent = pass.passRate + '%';
        document.getElementById('statExcellent').textContent = dist.values?.[0] || 0;
        document.getElementById('statFail').textContent = dist.values?.[4] || 0;

        renderDistribution(dist);
        renderPassRate(pass);
        renderCourseAvg(courseAvg);
        renderClassAvg(classAvg);

    } catch (err) {
        toast('加载统计数据失败：' + err.message, 'error');
    }
}

/* ============================================================
   深色主题图表配置
   ============================================================ */

const CHART_THEME = {
    text: '#8794ad',
    textLight: '#cbd5e1',
    axis: 'rgba(148, 163, 184, .22)',
    split: 'rgba(148, 163, 184, .08)',
    tooltipBg: 'rgba(20, 27, 48, .96)',
    tooltipBorder: 'rgba(99, 102, 241, .45)',
    palette: ['#6366f1', '#8b5cf6', '#06b6d4', '#22d3ee', '#a78bfa'],
    gradeColors: ['#10b981', '#38bdf8', '#6366f1', '#f59e0b', '#f43f5e']
};

function baseTooltip(extra) {
    return {
        backgroundColor: CHART_THEME.tooltipBg,
        borderColor: CHART_THEME.tooltipBorder,
        borderWidth: 1,
        padding: [10, 14],
        textStyle: { color: CHART_THEME.textLight, fontSize: 12.5 },
        extraCssText: 'border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.5);backdrop-filter:blur(8px);',
        ...extra
    };
}

function baseAxisCategory(data, opts = {}) {
    return {
        type: 'category',
        data,
        axisLine: { lineStyle: { color: CHART_THEME.axis } },
        axisTick: { show: false },
        axisLabel: {
            color: CHART_THEME.text,
            fontSize: 11.5,
            margin: 12,
            hideOverlap: true,
            ...(opts.axisLabel || {})
        }
    };
}

function baseAxisValue(opts = {}) {
    return {
        type: 'value',
        name: opts.name || '',
        nameTextStyle: { color: CHART_THEME.text, fontSize: 11.5, padding: [0, 0, 4, 0] },
        min: opts.min,
        max: opts.max,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: CHART_THEME.split, type: 'dashed' } },
        axisLabel: { color: CHART_THEME.text, fontSize: 11.5 }
    };
}

function initChart(domId) {
    const el = document.getElementById(domId);
    if (!el) return null;
    if (charts[domId]) {
        charts[domId].dispose();
    }
    charts[domId] = echarts.init(el, null, { renderer: 'canvas' });
    return charts[domId];
}

function renderDistribution(data) {
    const chart = initChart('chartDistribution');
    if (!chart) return;
    chart.setOption({
        tooltip: baseTooltip({ trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(99,102,241,.1)' } } }),
        grid: { left: 48, right: 26, top: 34, bottom: 48 },
        xAxis: baseAxisCategory(data.categories, { axisLabel: { fontSize: 11, rotate: 0 } }),
        yAxis: baseAxisValue({ name: '人数', minInterval: 1 }),
        series: [{
            type: 'bar',
            data: data.values.map((v, i) => ({
                value: v,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: CHART_THEME.gradeColors[i] },
                        { offset: 1, color: CHART_THEME.gradeColors[i] + '44' }
                    ]),
                    borderRadius: [6, 6, 0, 0],
                    shadowColor: CHART_THEME.gradeColors[i] + '66',
                    shadowBlur: 12,
                    shadowOffsetY: 2
                }
            })),
            barWidth: '52%',
            label: {
                show: true,
                position: 'top',
                color: CHART_THEME.textLight,
                fontSize: 12,
                fontWeight: 600
            }
        }]
    });
}

function renderPassRate(data) {
    const chart = initChart('chartPassRate');
    if (!chart) return;
    chart.setOption({
        tooltip: baseTooltip({ trigger: 'item', formatter: '{b}: {c} 人 ({d}%)' }),
        legend: {
            bottom: 6,
            itemWidth: 10,
            itemHeight: 10,
            itemGap: 22,
            textStyle: { color: CHART_THEME.text, fontSize: 12 },
            icon: 'roundRect'
        },
        series: [{
            type: 'pie',
            radius: ['48%', '72%'],
            center: ['50%', '44%'],
            avoidLabelOverlap: true,
            itemStyle: {
                borderColor: '#0d1322',
                borderWidth: 3,
                borderRadius: 4
            },
            data: data.data.map(d => ({
                ...d,
                itemStyle: {
                    color: d.name === '及格'
                        ? new echarts.graphic.LinearGradient(0, 0, 1, 1, [
                            { offset: 0, color: '#10b981' },
                            { offset: 1, color: '#059669' }
                        ])
                        : new echarts.graphic.LinearGradient(0, 0, 1, 1, [
                            { offset: 0, color: '#f43f5e' },
                            { offset: 1, color: '#be123c' }
                        ]),
                    shadowBlur: 16,
                    shadowColor: d.name === '及格' ? 'rgba(16,185,129,.4)' : 'rgba(244,63,94,.4)',
                    borderColor: '#0d1322',
                    borderWidth: 3,
                    borderRadius: 4
                }
            })),
            label: {
                show: true,
                formatter: '{b}\n{c} 人',
                color: CHART_THEME.textLight,
                fontSize: 11.5,
                lineHeight: 17
            },
            labelLine: {
                lineStyle: { color: CHART_THEME.axis },
                length: 8,
                length2: 12
            },
            emphasis: {
                scale: true,
                scaleSize: 6,
                itemStyle: { shadowBlur: 26 }
            }
        }]
    });
}

function renderCourseAvg(data) {
    const chart = initChart('chartCourseAvg');
    if (!chart) return;

    // 根据实际数据动态计算 Y 轴范围，避免折线贴边
    const allVals = [...(data.average || []), ...(data.max || []), ...(data.min || [])]
        .map(Number).filter(v => !isNaN(v));
    const dataMin = allVals.length ? Math.min(...allVals) : 0;
    const dataMax = allVals.length ? Math.max(...allVals) : 100;
    const pad = 8;
    const yMin = Math.max(0, Math.floor((dataMin - pad) / 5) * 5);
    const yMax = Math.min(100, Math.ceil((dataMax + pad) / 5) * 5);

    chart.setOption({
        tooltip: baseTooltip({ trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(99,102,241,.1)' } } }),
        legend: {
            top: 0,
            itemWidth: 14,
            itemHeight: 9,
            itemGap: 18,
            textStyle: { color: CHART_THEME.text, fontSize: 11.5 },
            icon: 'roundRect'
        },
        grid: { left: 46, right: 26, top: 44, bottom: 58 },
        xAxis: baseAxisCategory(data.courses, { axisLabel: { fontSize: 10.5, rotate: 16, interval: 0, margin: 10 } }),
        yAxis: baseAxisValue({ min: yMin, max: yMax }),
        series: [
            {
                name: '平均分',
                type: 'bar',
                data: data.average,
                barWidth: '30%',
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#8b5cf6' },
                        { offset: 1, color: 'rgba(99,102,241,.22)' }
                    ]),
                    borderRadius: [6, 6, 0, 0],
                    shadowColor: 'rgba(139,92,246,.45)',
                    shadowBlur: 14
                },
                label: {
                    show: true,
                    position: 'top',
                    color: CHART_THEME.textLight,
                    fontSize: 10.5,
                    fontWeight: 600,
                    formatter: '{c}'
                }
            },
            {
                name: '最高分',
                type: 'line',
                data: data.max,
                smooth: true,
                symbol: 'circle',
                symbolSize: 7,
                lineStyle: { width: 2.5, color: '#10b981', shadowColor: 'rgba(16,185,129,.55)', shadowBlur: 10 },
                itemStyle: { color: '#10b981', borderColor: '#0d1322', borderWidth: 2 },
                label: {
                    show: true,
                    position: 'top',
                    distance: 6,
                    color: '#10b981',
                    fontSize: 10,
                    formatter: '{c}'
                }
            },
            {
                name: '最低分',
                type: 'line',
                data: data.min,
                smooth: true,
                symbol: 'circle',
                symbolSize: 7,
                lineStyle: { width: 2.5, color: '#f43f5e', shadowColor: 'rgba(244,63,94,.55)', shadowBlur: 10 },
                itemStyle: { color: '#f43f5e', borderColor: '#0d1322', borderWidth: 2 },
                label: {
                    show: true,
                    position: 'bottom',
                    distance: 6,
                    color: '#f43f5e',
                    fontSize: 10,
                    formatter: '{c}'
                }
            }
        ]
    });
}

function renderClassAvg(data) {
    const chart = initChart('chartClassAvg');
    if (!chart) return;
    chart.setOption({
        tooltip: baseTooltip({ trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(99,102,241,.1)' } } }),
        grid: { left: 48, right: 26, top: 34, bottom: 48 },
        xAxis: baseAxisCategory(data.classes),
        yAxis: baseAxisValue({ name: '平均分', min: 0, max: 100 }),
        series: [{
            type: 'bar',
            data: data.average.map((v, i) => ({
                value: v,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: CHART_THEME.palette[i % CHART_THEME.palette.length] },
                        { offset: 1, color: CHART_THEME.palette[i % CHART_THEME.palette.length] + '3d' }
                    ]),
                    borderRadius: [7, 7, 0, 0],
                    shadowColor: CHART_THEME.palette[i % CHART_THEME.palette.length] + '70',
                    shadowBlur: 16,
                    shadowOffsetY: 2
                }
            })),
            barWidth: '46%',
            label: {
                show: true,
                position: 'top',
                color: CHART_THEME.textLight,
                fontSize: 12,
                fontWeight: 600
            }
        }]
    });
}

window.addEventListener('resize', () => {
    Object.values(charts).forEach(c => c && c.resize());
});

// ============================================================
//  成绩列表
// ============================================================
async function loadScores() {
    try {
        const semester = document.getElementById('semesterFilter')?.value || '';

        // 填充学期下拉
        const select = document.getElementById('semesterFilter');
        if (select && select.options.length <= 1) {
            const sems = await API.semesters();
            sems.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s;
                opt.textContent = s;
                select.appendChild(opt);
            });
        }

        const list = await API.listScores(semester);
        const tbody = document.getElementById('scoreTableBody');
        tbody.innerHTML = '';

        if (!list.length) {
            tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:#94a3b8;padding:30px">暂无成绩数据</td></tr>';
            return;
        }

        list.forEach(r => {
            const total = r.totalScore == null ? '-' : r.totalScore;
            const cls = r.totalScore != null && Number(r.totalScore) < 60 ? 'score-fail' : 'score-good';
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${r.stuNo || ''}</td>
                <td>${r.studentName || ''}</td>
                <td>${r.className || ''}</td>
                <td>${r.courseName || ''}</td>
                <td>${r.usualScore ?? '-'}</td>
                <td>${r.midtermScore ?? '-'}</td>
                <td>${r.finalScore ?? '-'}</td>
                <td class="${cls}">${total}</td>
                <td>${r.gradePoint ?? '-'}</td>
                <td>${r.semester || ''}</td>
            `;
            tbody.appendChild(tr);
        });

        // 学生无权录入
        const btn = document.getElementById('btnAddScore');
        if (btn) {
            btn.style.display = currentUser.permissions.includes('score:input') ? 'inline-block' : 'none';
        }

    } catch (err) {
        toast('加载成绩失败：' + err.message, 'error');
    }
}

// ============================================================
//  学生管理
// ============================================================
async function loadStudents() {
    try {
        const list = await API.listStudents();
        const tbody = document.getElementById('studentTableBody');
        tbody.innerHTML = '';
        list.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${r.stuNo}</td>
                <td>${r.realName}</td>
                <td>${r.gender === 1 ? '男' : '女'}</td>
                <td>${r.className || ''}</td>
                <td>${r.enrollYear || ''}</td>
                <td>${r.username}</td>
                <td>${r.phone || ''}</td>
                <td>
                    <button class="btn-danger-link" onclick="delStudent(${r.id})">删除</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        toast('加载学生失败：' + err.message, 'error');
    }
}

async function delStudent(id) {
    if (!confirm('确定删除该学生吗？')) return;
    try {
        await API.deleteStudent(id);
        toast('删除成功', 'success');
        loadStudents();
    } catch (err) {
        toast(err.message, 'error');
    }
}

// ============================================================
//  教师管理
// ============================================================
async function loadTeachers() {
    try {
        const list = await API.listTeachers();
        const tbody = document.getElementById('teacherTableBody');
        tbody.innerHTML = '';
        list.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${r.teacherNo}</td>
                <td>${r.realName}</td>
                <td>${r.gender === 1 ? '男' : '女'}</td>
                <td>${r.title || ''}</td>
                <td>${r.username}</td>
                <td>${r.phone || ''}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        toast('加载教师失败：' + err.message, 'error');
    }
}

// ============================================================
//  课程管理
// ============================================================
async function loadCourses() {
    try {
        const list = await API.listCourses();
        const tbody = document.getElementById('courseTableBody');
        tbody.innerHTML = '';
        list.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${r.courseCode}</td>
                <td>${r.courseName}</td>
                <td>${r.credit}</td>
                <td>${r.courseType === 1 ? '必修' : '选修'}</td>
                <td>${r.status === 1 ? '正常' : '停用'}</td>
                <td><button class="btn-danger-link" onclick="delCourse(${r.id})">删除</button></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        toast('加载课程失败：' + err.message, 'error');
    }
}

async function delCourse(id) {
    if (!confirm('确定删除该课程吗？关联成绩也会被删除！')) return;
    try {
        await API.deleteCourse(id);
        toast('删除成功', 'success');
        loadCourses();
    } catch (err) {
        toast(err.message, 'error');
    }
}

// ============================================================
//  审计日志
// ============================================================
async function loadLogs() {
    try {
        const list = await API.listScoreLogs();
        const tbody = document.getElementById('logTableBody');
        tbody.innerHTML = '';
        list.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${r.operateTime || ''}</td>
                <td>${r.scoreId}</td>
                <td>${r.operatorId}</td>
                <td>${r.action === 'INSERT' ? '录入' : '修改'}</td>
                <td>${r.oldValue || '-'}</td>
                <td>${r.newValue || '-'}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        toast('加载日志失败：' + err.message, 'error');
    }
}

// ============================================================
//  弹窗通用
// ============================================================
function openModal(title, bodyHtml, onSubmit) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').innerHTML = bodyHtml;
    document.getElementById('modal').style.display = 'flex';
    modalSubmitHandler = onSubmit;
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
    modalSubmitHandler = null;
}

function submitModal() {
    if (modalSubmitHandler) {
        modalSubmitHandler();
    }
}

// ---------- 成绩录入弹窗 ----------
async function openScoreModal() {
    const [students, courses] = await Promise.all([API.listStudents(), API.listCourses()]);

    const stuOpts = students.map(s =>
        `<option value="${s.id}">${s.stuNo} ${s.realName}</option>`).join('');
    const courseOpts = courses.map(c =>
        `<option value="${c.id}">${c.courseName}</option>`).join('');

    openModal('录入成绩', `
        <div class="form-group">
            <label>学生</label>
            <select id="mStudent">${stuOpts}</select>
        </div>
        <div class="form-group">
            <label>课程</label>
            <select id="mCourse">${courseOpts}</select>
        </div>
        <div class="form-group">
            <label>学期</label>
            <input type="text" id="mSemester" value="2025-2026-1">
        </div>
        <div class="form-group">
            <label>平时成绩（权重 30%）</label>
            <input type="number" id="mUsual" min="0" max="100" step="0.5" placeholder="0-100">
        </div>
        <div class="form-group">
            <label>期中成绩（权重 20%）</label>
            <input type="number" id="mMidterm" min="0" max="100" step="0.5" placeholder="0-100">
        </div>
        <div class="form-group">
            <label>期末成绩（权重 50%）</label>
            <input type="number" id="mFinal" min="0" max="100" step="0.5" placeholder="0-100">
        </div>
        <p style="font-size:12px;color:#64748b;margin-top:8px">
            总评将按课程折算规则自动计算
        </p>
    `, async () => {
        const data = {
            studentId: Number(document.getElementById('mStudent').value),
            courseId: Number(document.getElementById('mCourse').value),
            semester: document.getElementById('mSemester').value.trim(),
            usualScore: numOrNull('mUsual'),
            midtermScore: numOrNull('mMidterm'),
            finalScore: numOrNull('mFinal')
        };

        if (!data.semester) {
            toast('请填写学期', 'error');
            return;
        }

        try {
            const res = await API.saveScore(data);
            closeModal();
            toast(`保存成功！总评 ${res.totalScore} 分，绩点 ${res.gradePoint}`, 'success');
            loadScores();
            loadDashboard();
        } catch (err) {
            toast(err.message, 'error');
        }
    });
}

// ---------- 学生新增弹窗 ----------
async function openStudentModal() {
    const classes = await API.listClasses();
    const classOpts = classes.map(c =>
        `<option value="${c.id}">${c.className}</option>`).join('');

    openModal('新增学生', `
        <div class="form-group"><label>学号</label>
            <input type="text" id="sStuNo" placeholder="如 2023010106"></div>
        <div class="form-group"><label>姓名</label>
            <input type="text" id="sName"></div>
        <div class="form-group"><label>登录账号</label>
            <input type="text" id="sUsername" placeholder="建议用学号"></div>
        <div class="form-group"><label>初始密码</label>
            <input type="text" id="sPassword" value="123456"></div>
        <div class="form-group"><label>性别</label>
            <select id="sGender"><option value="1">男</option><option value="0">女</option></select></div>
        <div class="form-group"><label>班级</label>
            <select id="sClass">${classOpts}</select></div>
        <div class="form-group"><label>入学年份</label>
            <input type="number" id="sYear" value="2023"></div>
    `, async () => {
        const data = {
            stuNo: document.getElementById('sStuNo').value.trim(),
            realName: document.getElementById('sName').value.trim(),
            username: document.getElementById('sUsername').value.trim(),
            password: document.getElementById('sPassword').value,
            gender: Number(document.getElementById('sGender').value),
            classId: Number(document.getElementById('sClass').value),
            enrollYear: Number(document.getElementById('sYear').value)
        };
        try {
            await API.addStudent(data);
            closeModal();
            toast('新增成功', 'success');
            loadStudents();
        } catch (err) {
            toast(err.message, 'error');
        }
    });
}

// ---------- 教师新增弹窗 ----------
function openTeacherModal() {
    openModal('新增教师', `
        <div class="form-group"><label>工号</label>
            <input type="text" id="tNo" placeholder="如 T2003"></div>
        <div class="form-group"><label>姓名</label>
            <input type="text" id="tName"></div>
        <div class="form-group"><label>登录账号</label>
            <input type="text" id="tUsername"></div>
        <div class="form-group"><label>初始密码</label>
            <input type="text" id="tPassword" value="123456"></div>
        <div class="form-group"><label>性别</label>
            <select id="tGender"><option value="1">男</option><option value="0">女</option></select></div>
        <div class="form-group"><label>职称</label>
            <input type="text" id="tTitle" placeholder="如 讲师"></div>
    `, async () => {
        const data = {
            teacherNo: document.getElementById('tNo').value.trim(),
            realName: document.getElementById('tName').value.trim(),
            username: document.getElementById('tUsername').value.trim(),
            password: document.getElementById('tPassword').value,
            gender: Number(document.getElementById('tGender').value),
            title: document.getElementById('tTitle').value.trim()
        };
        try {
            await API.addTeacher(data);
            closeModal();
            toast('新增成功', 'success');
            loadTeachers();
        } catch (err) {
            toast(err.message, 'error');
        }
    });
}

// ---------- 课程新增弹窗 ----------
function openCourseModal() {
    openModal('新增课程', `
        <div class="form-group"><label>课程编码</label>
            <input type="text" id="cCode" placeholder="如 CS104"></div>
        <div class="form-group"><label>课程名称</label>
            <input type="text" id="cName"></div>
        <div class="form-group"><label>学分</label>
            <input type="number" id="cCredit" value="3" step="0.5" min="0"></div>
        <div class="form-group"><label>类型</label>
            <select id="cType"><option value="1">必修</option><option value="2">选修</option></select></div>
    `, async () => {
        const data = {
            courseCode: document.getElementById('cCode').value.trim(),
            courseName: document.getElementById('cName').value.trim(),
            credit: document.getElementById('cCredit').value,
            courseType: Number(document.getElementById('cType').value)
        };
        try {
            await API.addCourse(data);
            closeModal();
            toast('新增成功', 'success');
            loadCourses();
        } catch (err) {
            toast(err.message, 'error');
        }
    });
}

// ============================================================
//  工具
// ============================================================
function numOrNull(id) {
    const v = document.getElementById(id).value;
    if (v === '' || v === null) return null;
    return Number(v);
}

let toastTimer = null;
function toast(msg, type = '') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = 'toast show ' + type;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
        el.className = 'toast ' + type;
    }, 3000);
}
