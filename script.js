// --------- cached DOM ----------
const stateSelectRole = document.getElementById("state-select-role");
const portals = document.querySelectorAll(".portal");
const roleButtons = document.querySelectorAll(".role-button[data-role]");
const switchRoleBtns = document.querySelectorAll(".switch-role-btn");
const roleLabels = document.querySelectorAll("[data-role-label]");
const clubSelectToggle = document.querySelector(".club-dropdown .dropdown-toggle");
const clubDropdown = document.querySelector(".club-dropdown");
const bootBanner = document.getElementById("boot-banner");
const debugOverlay = document.getElementById("debug-overlay");
const debugText = document.getElementById("debug-text");

const calendarInstances = new Map();
const calendarTimeZone = "Asia/Almaty";

let currentUser = null;
let authBlocked = false;
let debugEnabled = false;
const debugLines = [];

function enableDebug(reason) {
  if (debugEnabled) return;
  debugEnabled = true;
  if (debugOverlay) debugOverlay.classList.remove("hidden");
  addDebugLine(`debug enabled: ${reason}`);
  updateDebugSnapshot();
}

function addDebugLine(message) {
  const timestamp = new Date().toISOString();
  debugLines.push(`[${timestamp}] ${message}`);
  if (debugLines.length > 50) debugLines.shift();
  updateDebugSnapshot();
}

function getStoredUserSafe() {
  try {
    const stored = localStorage.getItem("roomly_user");
    return stored ? JSON.parse(stored) : null;
  } catch (err) {
    return null;
  }
}

function updateDebugSnapshot() {
  if (!debugEnabled || !debugText) return;
  const tg = window.Telegram && window.Telegram.WebApp;
  const storedUser = getStoredUserSafe();
  const visiblePortal = document.querySelector(".portal:not(.hidden)");
  const snapshot = [
    `href: ${window.location.href}`,
    `readyState: ${document.readyState}`,
    `telegram: ${Boolean(tg)}`,
    `initData length: ${tg && tg.initData ? tg.initData.length : 0}`,
    `authBlocked: ${authBlocked}`,
    `storedUser: ${storedUser ? `${storedUser.id || ""} ${storedUser.role || ""} ${storedUser.email || ""}`.trim() : "none"}`,
    `visiblePortal: ${visiblePortal ? visiblePortal.dataset.portal : "none"}`,
    `selectRoleHidden: ${stateSelectRole ? stateSelectRole.classList.contains("hidden") : "missing"}`,
    `portals: ${portals.length}`
  ].join("\n");

  debugText.textContent = `${debugLines.join("\n")}\n\n${snapshot}`;
}

if (new URLSearchParams(window.location.search).get("debug") === "1") {
  enableDebug("query");
}

window.addEventListener("error", (event) => {
  showSelectRole();
  setAuthMessage("Something went wrong. Please reopen the app.");
  enableDebug("window error");
  addDebugLine(`error: ${event.message || "unknown"}`);
});

window.addEventListener("unhandledrejection", (event) => {
  showSelectRole();
  setAuthMessage("Something went wrong. Please reopen the app.");
  enableDebug("unhandled rejection");
  addDebugLine(`rejection: ${event.reason ? String(event.reason) : "unknown"}`);
});

// --------- helpers ----------
function hideAllPortals() {
  portals.forEach((portal) => portal.classList.add("hidden"));
}

function showSelectRole() {
  hideAllPortals();
  if (stateSelectRole) stateSelectRole.classList.remove("hidden");
  updateDebugSnapshot();
}

function openPortal(roleKey) {
  hideAllPortals();
  if (stateSelectRole) stateSelectRole.classList.add("hidden");
  let portal = document.querySelector(`.portal[data-portal="${roleKey}"]`);
  if (!portal && roleKey === "admin") {
    portal = document.querySelector('.portal[data-portal="administration"]');
  }
  if (!portal && roleKey === "administration") {
    portal = document.querySelector('.portal[data-portal="admin"]');
  }
  if (!portal) {
    showSelectRole();
    setAuthMessage("Portal not found. Please reload the app.");
    return;
  }
  portal.classList.remove("hidden");
  activateCalendars(portal);
  refreshPortalData(portal);
  if (portal.dataset.portal === "club") {
    loadClubOptions();
  }
  updateDebugSnapshot();
}

function setRoleLabels(labelText) {
  roleLabels.forEach((el) => {
    el.textContent = `Role: ${labelText}`;
  });
}

function getAllowedRoles(userRole) {
  if (!userRole) return [];
  if (userRole === "admin" || userRole === "administration") {
    return ["student", "club", "administration"];
  }
  if (userRole === "club_leader") return ["student", "club"];
  return ["student"];
}

function mapUserRoleToPortal(userRole) {
  if (userRole === "admin" || userRole === "administration") return "administration";
  if (userRole === "club_leader") return "club";
  return "student";
}

function mapUserRoleToLabel(userRole) {
  if (userRole === "admin" || userRole === "administration") return "admin";
  if (userRole === "club_leader") return "club leader";
  return "student";
}

function applyRoleAccess(userRole) {
  const allowed = getAllowedRoles(userRole);
  roleButtons.forEach((btn) => {
    const role = btn.dataset.role;
    const isAllowed = allowed.includes(role);
    btn.classList.toggle("disabled", !isAllowed);
    btn.setAttribute("aria-disabled", isAllowed ? "false" : "true");
  });
}

function setAuthMessage(message) {
  const el = document.getElementById("auth-message");
  if (!el) return;
  if (message) {
    el.textContent = message;
    el.classList.remove("hidden");
  } else {
    el.classList.add("hidden");
  }
}

function ensureVisibleUI() {
  const hasPortalVisible = Boolean(document.querySelector(".portal:not(.hidden)"));
  const selectVisible = stateSelectRole && !stateSelectRole.classList.contains("hidden");
  if (!hasPortalVisible && !selectVisible) {
    showSelectRole();
    setAuthMessage("UI failed to load. Please reopen the app.");
    enableDebug("ui hidden");
    addDebugLine("no portal or select role visible");
  }
}

function formatDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  return date.toLocaleString("en-GB", {
    timeZone: calendarTimeZone,
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function showStatus(el, message, type) {
  if (!el) return;
  el.textContent = message;
  el.classList.remove("error", "success");
  if (type) el.classList.add(type);
}

function buildDateTime(dateStr, timeStr) {
  if (!dateStr || !timeStr) return null;
  return `${dateStr}T${timeStr}:00`;
}

function diffMinutes(startTime, endTime) {
  const [sh, sm] = startTime.split(":").map(Number);
  const [eh, em] = endTime.split(":").map(Number);
  const startMinutes = sh * 60 + sm;
  const endMinutes = eh * 60 + em;
  return endMinutes - startMinutes;
}

function buildRRule(repeat, repeatUntil) {
  if (!repeat || repeat === "none") return null;
  const freq = repeat.toUpperCase();
  let rule = `FREQ=${freq}`;
  if (repeatUntil) {
    const until = repeatUntil.replace(/-/g, "");
    rule += `;UNTIL=${until}T235959`;
  }
  return rule;
}

// --------- auth ----------
async function bootstrapAuth() {
  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg && typeof tg.ready === "function") {
    tg.ready();
  }
  if (tg && typeof tg.expand === "function") {
    tg.expand();
  }
  if (tg && tg.initData) {
    try {
      const res = await fetch("/api/auth/telegram", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ init_data: tg.initData })
      });
      if (res.status === 403) {
        authBlocked = true;
        setAuthMessage("Email required. Please send /email you@domain.com to the bot, then reopen the app.");
      } else if (res.ok) {
        const data = await res.json();
        if (data.access_token) {
          localStorage.setItem("roomly_token", data.access_token);
        }
        if (data.user) {
          localStorage.setItem("roomly_user", JSON.stringify(data.user));
        }
        setAuthMessage("");
      } else {
        setAuthMessage("Auth failed. Please reopen the app.");
      }
    } catch (err) {
      console.warn("Auth failed", err);
      setAuthMessage("Auth failed. Please reopen the app.");
      enableDebug("auth fetch error");
      addDebugLine(`auth exception: ${err ? String(err) : "unknown"}`);
    }
  }

  const stored = localStorage.getItem("roomly_user");
  if (stored) {
    try {
      currentUser = JSON.parse(stored);
    } catch (err) {
      currentUser = null;
      localStorage.removeItem("roomly_user");
    }
  } else {
    currentUser = null;
  }

  if (authBlocked) {
    applyRoleAccess(null);
    showSelectRole();
    addDebugLine("auth blocked: email required");
    return;
  }

  if (currentUser) {
    applyRoleAccess(currentUser.role);
    setRoleLabels(mapUserRoleToLabel(currentUser.role));
    openPortal(mapUserRoleToPortal(currentUser.role));
  } else {
    applyRoleAccess("student");
    setRoleLabels("student");
    showSelectRole();
  }

  setTimeout(ensureVisibleUI, 500);
  if (bootBanner) bootBanner.classList.add("hidden");
  updateDebugSnapshot();
}

function getAuthHeaders() {
  const token = localStorage.getItem("roomly_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// --------- role switching ----------
roleButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    if (btn.classList.contains("disabled")) return;
    const role = btn.dataset.role;
    openPortal(role);
  });
});

switchRoleBtns.forEach((btn) => btn.addEventListener("click", showSelectRole));

// --------- Tabs: scope tabs to their portal/container ----------
document.querySelectorAll(".student-tabs").forEach((tabsContainer) => {
  const portalRoot =
    tabsContainer.closest("[data-portal]") ||
    tabsContainer.closest(".container") ||
    document;
  const tabs = Array.from(tabsContainer.querySelectorAll(".tab"));
  const contents = Array.from(portalRoot.querySelectorAll(".tab-content"));

  if (tabs.length === 0 || contents.length === 0) return;

  function activateTab(index) {
    tabs.forEach((t, i) => t.classList.toggle("active", i === index));
    contents.forEach((c, i) => {
      if (i === index) c.classList.remove("hidden");
      else c.classList.add("hidden");
    });
    activateCalendars(portalRoot);
    refreshPortalData(portalRoot);
  }

  activateTab(0);
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activateTab(index));
  });
});

// --------- Dropdown (club select) ----------
function setClubToggleLabel(label) {
  if (!clubSelectToggle) return;
  const textNode = Array.from(clubSelectToggle.childNodes).find(
    (node) => node.nodeType === Node.TEXT_NODE
  );
  if (textNode) {
    textNode.nodeValue = `${label} `;
  } else {
    clubSelectToggle.textContent = label;
  }
}

function applyClubSelection(li, menu) {
  if (!clubSelectToggle || !li || !menu || li.classList.contains("disabled")) return;
  setClubToggleLabel(li.textContent.trim());
  if (li.dataset.clubId) clubSelectToggle.dataset.clubId = li.dataset.clubId;
  clubSelectToggle.dataset.clubName = li.textContent.trim();
  menu.classList.add("hidden");
  menu.querySelectorAll("li").forEach((x) => x.classList.remove("selected"));
  li.classList.add("selected");
  loadClubMembers();
}

document.querySelectorAll(".club-dropdown").forEach((dd) => {
  const btn = dd.querySelector(".dropdown-toggle");
  const menu = dd.querySelector(".dropdown-menu");

  if (!btn || !menu) return;

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (btn.getAttribute("aria-disabled") === "true") return;
    menu.classList.toggle("hidden");
  });

  menu.addEventListener("click", (e) => {
    const li = e.target.closest("li");
    if (!li) return;
    e.stopPropagation();
    applyClubSelection(li, menu);
  });

  document.addEventListener("click", (e) => {
    if (!dd.contains(e.target)) menu.classList.add("hidden");
  });
});

async function loadClubOptions() {
  if (!clubDropdown || !clubSelectToggle) return;
  const menu = clubDropdown.querySelector(".dropdown-menu");
  if (!menu) return;

  setClubToggleLabel("Loading clubs");
  clubSelectToggle.dataset.clubId = "";
  clubSelectToggle.dataset.clubName = "";
  clubSelectToggle.setAttribute("aria-disabled", "true");
  menu.innerHTML = "";

  try {
    const res = await fetch("/api/clubs/my", { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("clubs fetch failed");
    const clubs = await res.json();

    if (!clubs.length) {
      setClubToggleLabel("No clubs assigned");
      clubSelectToggle.dataset.clubName = "";
      const li = document.createElement("li");
      li.textContent = "No clubs assigned";
      li.classList.add("disabled");
      menu.appendChild(li);
      return;
    }

    clubs.forEach((club, index) => {
      const li = document.createElement("li");
      li.textContent = club.name;
      li.dataset.clubId = club.id;
      if (index === 0) {
        li.classList.add("selected");
      }
      menu.appendChild(li);
    });

    clubSelectToggle.removeAttribute("aria-disabled");
    clubSelectToggle.dataset.clubId = String(clubs[0].id);
    clubSelectToggle.dataset.clubName = clubs[0].name;
    setClubToggleLabel(clubs[0].name);
    loadClubMembers();
  } catch (err) {
    setClubToggleLabel("Clubs unavailable");
    clubSelectToggle.dataset.clubName = "";
    const li = document.createElement("li");
    li.textContent = "Clubs unavailable";
    li.classList.add("disabled");
    menu.appendChild(li);
  }
}

// --------- Calendar ----------
function getCalendarRole(el) {
  if (!el) return "student";
  if (el.id === "calendar-club") return "club";
  if (el.id === "calendar-admin") return "admin";
  return "student";
}

function fetchCalendarEvents(info, successCallback, failureCallback) {
  const params = new URLSearchParams({
    start: info.startStr,
    end: info.endStr
  });

  fetch(`/api/calendar/events?${params.toString()}`, {
    headers: getAuthHeaders()
  })
    .then((res) => (res.ok ? res.json() : Promise.reject(res)))
    .then((data) => successCallback(data))
    .catch((err) => {
      console.warn("Calendar events failed", err);
      failureCallback(err);
    });
}

function buildCalendar(el, role) {
  return new FullCalendar.Calendar(el, {
    plugins: FullCalendar.Rrule ? [FullCalendar.Rrule] : [],
    timeZone: calendarTimeZone,
    initialView: "dayGridMonth",
    height: "auto",
    selectable: false,
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "dayGridMonth,timeGridWeek,timeGridDay"
    },
    events: fetchCalendarEvents,
    eventClassNames: (arg) => {
      const classes = [];
      const eventType = arg.event.extendedProps.event_type;
      const status = arg.event.extendedProps.status;
      if (eventType) classes.push(`event-${eventType}`);
      if (status) classes.push(`status-${status}`);
      return classes;
    }
  });
}

function isVisible(el) {
  return el.offsetParent !== null;
}

function activateCalendars(portal) {
  const calendarEls = portal.querySelectorAll(".calendar");
  if (calendarEls.length === 0) return;

  calendarEls.forEach((el) => {
    if (!calendarInstances.has(el)) {
      const role = getCalendarRole(el);
      calendarInstances.set(el, buildCalendar(el, role));
    }

    const calendar = calendarInstances.get(el);
    if (calendar && isVisible(el)) {
      calendar.render();
      calendar.refetchEvents();
    }
  });
}

// --------- Lists ----------
async function fetchEvents(params = {}) {
  const url = new URL("/api/calendar/events", window.location.origin);
  if (params.start) url.searchParams.set("start", params.start);
  if (params.end) url.searchParams.set("end", params.end);

  const res = await fetch(url.toString(), { headers: getAuthHeaders() });
  if (!res.ok) throw new Error("events fetch failed");
  return res.json();
}

function renderEventList(container, events, options = {}) {
  if (!container) return;
  container.innerHTML = "";

  if (!events.length) {
    container.innerHTML = '<div class="event-item">No events to show.</div>';
    return;
  }

  events.forEach((event) => {
    const item = document.createElement("div");
    item.className = "event-item";

    const meta = document.createElement("div");
    const title = document.createElement("div");
    title.className = "event-title";
    title.textContent = event.title;

    const detail = document.createElement("div");
    detail.className = "event-meta";
    detail.innerHTML = `
      <span>${formatDateTime(event.start)}</span>
      <span>${event.event_type || ""}</span>
      <span>${event.status || ""}</span>
    `;

    meta.appendChild(title);
    meta.appendChild(detail);

    item.appendChild(meta);

    if (options.actions) {
      const actions = document.createElement("div");
      actions.className = "event-actions";
      actions.innerHTML = options.actions(event);
      item.appendChild(actions);
    }

    container.appendChild(item);
  });
}

async function loadStudentUpcoming() {
  const container = document.getElementById("student-upcoming");
  if (!container) return;

  const start = new Date();
  const end = new Date();
  end.setDate(end.getDate() + 30);

  try {
    const events = await fetchEvents({
      start: start.toISOString(),
      end: end.toISOString()
    });
    events.sort((a, b) => new Date(a.start) - new Date(b.start));
    renderEventList(container, events.slice(0, 8));
  } catch (err) {
    renderEventList(container, []);
  }
}

function updateRoomsTime() {
  const timeEls = document.querySelectorAll("[data-rooms-time]");
  if (!timeEls.length) return;
  const now = new Date();
  const timeLabel = now.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit"
  });
  timeEls.forEach((el) => {
    el.textContent = `As of ${timeLabel}`;
  });
}

function renderRoomCards(container, rooms, options = {}) {
  if (!container) return;
  container.innerHTML = "";
  const showReserve = Boolean(options.reserve);

  if (!rooms.length) {
    container.innerHTML = '<div class="room-card">No rooms available.</div>';
    return;
  }

  rooms.forEach((room) => {
    const card = document.createElement("div");
    card.className = "room-card";
    const typeLabel = room.room_type || "Room";
    const building = room.building || "";
    const floor = room.floor || "";
    const capacity = room.capacity ? `${room.capacity} seats` : "";
    const statusLabel = room.is_active ? "Active" : "Inactive";
    const locationLabel = [building, floor].filter(Boolean).join(" ");

    card.innerHTML = `
      <div class="room-card-header">
        <h4 class="room-card-title">${room.code}</h4>
        <span class="room-tag">${typeLabel}</span>
      </div>
      <p class="room-floor">
        <span class="basic-icon">
          <img src="assets/img/location.png" alt="location"/>
        </span>
        ${locationLabel || "Location not set"}
      </p>
      <p class="room-seats">
        <span class="basic-icon">
          <img src="assets/img/user.png" alt="users"/>
        </span>
        ${capacity || "Capacity not set"}
      </p>
      <div class="room-equipment">
        <span class="eq-tag">${statusLabel}</span>
      </div>
      ${showReserve ? `<button class="reserve-room-btn" data-room-code="${room.code}">Reserve Room</button>` : ""}
    `;

    container.appendChild(card);
  });
}

async function loadAvailableRooms(targetId, options = {}) {
  const container = document.getElementById(targetId);
  if (!container) return;

  try {
    const res = await fetch("/api/rooms/available", { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("rooms fetch failed");
    const rooms = await res.json();
    renderRoomCards(container, rooms, options);
    updateRoomsTime();
  } catch (err) {
    renderRoomCards(container, [], options);
    updateRoomsTime();
  }
}

function renderClubList(container, clubs) {
  if (!container) return;
  container.innerHTML = "";
  if (!clubs.length) {
    container.innerHTML = '<div class="club-item">No clubs yet.</div>';
    return;
  }
  clubs.forEach((club) => {
    const item = document.createElement("div");
    item.className = "club-item";
    const canLeave = club.role !== "leader";
    item.innerHTML = `
      <div class="club-item-title">${club.name}</div>
      <div class="club-item-meta">${club.role || ""}</div>
      ${canLeave ? `<button class="btn-danger club-leave-btn" data-club-name="${club.name}">Leave</button>` : ""}
    `;
    container.appendChild(item);
  });
}

async function loadStudentClubs() {
  const container = document.getElementById("student-clubs");
  if (!container) return;
  try {
    const res = await fetch("/api/clubs/memberships", { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("clubs fetch failed");
    const clubs = await res.json();
    renderClubList(container, clubs);
  } catch (err) {
    renderClubList(container, []);
  }
}

function renderMemberList(container, members) {
  if (!container) return;
  container.innerHTML = "";
  if (!members.length) {
    container.innerHTML = '<div class="member-item">No members yet.</div>';
    return;
  }
  members.forEach((member) => {
    const item = document.createElement("div");
    item.className = "member-item";
    const nameLabel = member.full_name || member.email || "Member";
    item.innerHTML = `
      <div class="member-item-title">${nameLabel}</div>
      <div class="member-item-meta">${member.email || ""}</div>
      <div class="member-item-meta">${member.role || ""}</div>
    `;
    container.appendChild(item);
  });
}

async function loadClubMembers() {
  const container = document.getElementById("club-members-list");
  if (!container) return;
  const clubName = clubSelectToggle ? clubSelectToggle.dataset.clubName : "";
  if (!clubName) {
    container.innerHTML = '<div class="member-item">Select a club to view members.</div>';
    return;
  }

  try {
    const params = new URLSearchParams({ club_name: clubName });
    const res = await fetch(`/api/clubs/members?${params.toString()}`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error("members fetch failed");
    const members = await res.json();
    renderMemberList(container, members);
  } catch (err) {
    renderMemberList(container, []);
  }
}

async function loadClubRequests() {
  const container = document.getElementById("club-requests-list");
  if (!container) return;

  try {
    const events = await fetchEvents();
    events.sort((a, b) => (a.status || "").localeCompare(b.status || ""));
    renderEventList(container, events);
  } catch (err) {
    renderEventList(container, []);
  }
}

async function loadAdminApprovals() {
  const container = document.getElementById("admin-approvals-list");
  if (!container) return;

  try {
    const events = await fetchEvents();
    const pending = events.filter((event) => event.status === "pending");
    renderEventList(container, pending, {
      actions: (event) => `
        <span class="status-chip">${event.status}</span>
        <button class="btn-secondary" data-action="approve" data-id="${event.id}">Approve</button>
        <button class="btn-danger" data-action="reject" data-id="${event.id}">Reject</button>
      `
    });
  } catch (err) {
    renderEventList(container, []);
  }
}

function renderDataList(container, items, emptyMessage) {
  if (!container) return;
  container.innerHTML = "";
  if (!items.length) {
    container.innerHTML = `<div class="data-item">${emptyMessage}</div>`;
    return;
  }
  items.forEach((item) => container.appendChild(item));
}

async function loadAdminUsers() {
  const container = document.getElementById("admin-users-list");
  if (!container) return;
  try {
    const res = await fetch("/api/admin/users", { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("users fetch failed");
    const users = await res.json();
    const items = users.map((user) => {
      const el = document.createElement("div");
      el.className = "data-item";
      const nameLabel = user.full_name || user.email || `User ${user.id}`;
      el.innerHTML = `
        <div>
          <div class="data-item-title">${nameLabel}</div>
          <div class="data-item-meta">
            <span>${user.email || "no email"}</span>
            <span>${user.role || ""}</span>
            <span>ID ${user.id}</span>
          </div>
        </div>
        <div class="data-actions">
          <button class="btn-danger" data-action="delete-user" data-id="${user.id}">Delete</button>
        </div>
      `;
      return el;
    });
    renderDataList(container, items, "No users.");
  } catch (err) {
    renderDataList(container, [], "No users.");
  }
}

async function loadAdminClubs() {
  const container = document.getElementById("admin-clubs-list");
  if (!container) return;
  try {
    const res = await fetch("/api/admin/clubs", { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("clubs fetch failed");
    const clubs = await res.json();
    const items = clubs.map((club) => {
      const el = document.createElement("div");
      el.className = "data-item";
      el.innerHTML = `
        <div>
          <div class="data-item-title">${club.name}</div>
          <div class="data-item-meta">
            <span>ID ${club.id}</span>
            <span>Owner ${club.owner_user_id || "none"}</span>
          </div>
        </div>
        <div class="data-actions">
          <button class="btn-danger" data-action="delete-club" data-id="${club.id}">Delete</button>
        </div>
      `;
      return el;
    });
    renderDataList(container, items, "No clubs.");
  } catch (err) {
    renderDataList(container, [], "No clubs.");
  }
}

async function loadAdminClubMembers() {
  const container = document.getElementById("admin-club-members-list");
  if (!container) return;
  try {
    const res = await fetch("/api/admin/club-members", { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("members fetch failed");
    const members = await res.json();
    const items = members.map((member) => {
      const el = document.createElement("div");
      el.className = "data-item";
      el.innerHTML = `
        <div>
          <div class="data-item-title">${member.club_name}</div>
          <div class="data-item-meta">
            <span>${member.user_email || "no email"}</span>
            <span>${member.role || ""}</span>
            <span>Club ${member.club_id}</span>
            <span>User ${member.user_id}</span>
          </div>
        </div>
        <div class="data-actions">
          <button class="btn-danger" data-action="delete-club-member" data-club-id="${member.club_id}" data-user-id="${member.user_id}">Delete</button>
        </div>
      `;
      return el;
    });
    renderDataList(container, items, "No club members.");
  } catch (err) {
    renderDataList(container, [], "No club members.");
  }
}

async function loadAdminEvents() {
  const container = document.getElementById("admin-events-list");
  if (!container) return;
  try {
    const res = await fetch("/api/admin/events", { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("events fetch failed");
    const events = await res.json();
    const items = events.map((event) => {
      const el = document.createElement("div");
      el.className = "data-item";
      el.innerHTML = `
        <div>
          <div class="data-item-title">${event.title}</div>
          <div class="data-item-meta">
            <span>ID ${event.id}</span>
            <span>${event.event_type || ""}</span>
            <span>${event.status || ""}</span>
            <span>Club ${event.club_id || "-"}</span>
            <span>Room ${event.room_code || "-"}</span>
          </div>
        </div>
        <div class="data-actions">
          <button class="btn-danger" data-action="delete-event" data-id="${event.id}">Delete</button>
        </div>
      `;
      return el;
    });
    renderDataList(container, items, "No events.");
  } catch (err) {
    renderDataList(container, [], "No events.");
  }
}

async function loadAdminEventParticipants() {
  const container = document.getElementById("admin-event-participants-list");
  if (!container) return;
  try {
    const res = await fetch("/api/admin/event-participants", { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("participants fetch failed");
    const participants = await res.json();
    const items = participants.map((participant) => {
      const el = document.createElement("div");
      el.className = "data-item";
      el.innerHTML = `
        <div>
          <div class="data-item-title">Event ${participant.event_id}</div>
          <div class="data-item-meta">
            <span>User ${participant.user_id}</span>
            <span>${participant.user_email || "no email"}</span>
          </div>
        </div>
        <div class="data-actions">
          <button class="btn-danger" data-action="delete-event-participant" data-event-id="${participant.event_id}" data-user-id="${participant.user_id}">Delete</button>
        </div>
      `;
      return el;
    });
    renderDataList(container, items, "No event participants.");
  } catch (err) {
    renderDataList(container, [], "No event participants.");
  }
}

function loadAdminData() {
  loadAdminUsers();
  loadAdminClubs();
  loadAdminClubMembers();
  loadAdminEvents();
  loadAdminEventParticipants();
}

const adminRoomsByCode = new Map();

function renderAdminRooms(container, rooms) {
  if (!container) return;
  container.innerHTML = "";
  adminRoomsByCode.clear();

  if (!rooms.length) {
    container.innerHTML = '<div class="room-item">No rooms yet.</div>';
    return;
  }

  rooms.forEach((room) => {
    adminRoomsByCode.set(room.code, room);
    const item = document.createElement("div");
    item.className = "room-item";
    item.innerHTML = `
      <div>
        <div class="room-item-title">${room.code}</div>
        <div class="room-item-meta">
          <span>${room.building || ""}</span>
          <span>${room.floor || ""}</span>
          <span>${room.room_type || ""}</span>
          <span>${room.capacity ? `${room.capacity} seats` : ""}</span>
          <span>${room.is_active ? "active" : "inactive"}</span>
        </div>
      </div>
      <div class="data-actions">
        <button class="btn-secondary" data-action="edit-room" data-code="${room.code}">Edit</button>
        <button class="btn-danger" data-action="delete-room" data-code="${room.code}">Delete</button>
      </div>
    `;
    container.appendChild(item);
  });
}

async function loadAdminRooms() {
  const container = document.getElementById("admin-rooms-list");
  if (!container) return;

  try {
    const res = await fetch("/api/admin/rooms", { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("rooms fetch failed");
    const rooms = await res.json();
    renderAdminRooms(container, rooms);
  } catch (err) {
    renderAdminRooms(container, []);
  }
}

function refreshPortalData(portal) {
  const portalName = portal.dataset.portal;
  if (portalName === "student") {
    loadStudentUpcoming();
    loadStudentClubs();
    loadAvailableRooms("student-rooms-grid");
  }
  if (portalName === "club") {
    loadClubRequests();
    loadClubMembers();
    loadAvailableRooms("club-rooms-grid", { reserve: true });
  }
  if (portalName === "administration") {
    loadAdminApprovals();
    loadAdminRooms();
    loadAdminData();
  }
}

// --------- Admin actions ----------
const adminApprovalsList = document.getElementById("admin-approvals-list");
if (adminApprovalsList) {
  adminApprovalsList.addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-action]");
    if (!btn) return;

    const action = btn.dataset.action;
    const id = btn.dataset.id;
    if (!id || !action) return;

    try {
      const res = await fetch(`/api/admin/events/${id}/${action}`, {
        method: "POST",
        headers: getAuthHeaders()
      });
      if (!res.ok) throw new Error("action failed");
      await loadAdminApprovals();
      const adminPortal = document.querySelector('[data-portal="administration"]');
      if (adminPortal) activateCalendars(adminPortal);
    } catch (err) {
      console.warn("Admin action failed", err);
    }
  });
}

// --------- Forms ----------
const clubEventForm = document.getElementById("club-event-form");
if (clubEventForm) {
  clubEventForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const statusEl = document.getElementById("club-form-status");

    const formData = new FormData(clubEventForm);
    const title = String(formData.get("title") || "").trim();
    const date = String(formData.get("date") || "").trim();
    const startTime = String(formData.get("start_time") || "").trim();
    const endTime = String(formData.get("end_time") || "").trim();
    const repeat = String(formData.get("repeat") || "none");
    const repeatUntil = String(formData.get("repeat_until") || "").trim();
    const roomCode = String(formData.get("room_code") || "").trim();
    const description = String(formData.get("description") || "").trim();

    if (!title || !date || !startTime || !endTime) {
      showStatus(statusEl, "Fill in title, date, and time.", "error");
      return;
    }

    const durationMinutes = diffMinutes(startTime, endTime);
    if (durationMinutes <= 0) {
      showStatus(statusEl, "End time must be after start time.", "error");
      return;
    }

    const rrule = buildRRule(repeat, repeatUntil);
    const clubId = clubSelectToggle ? Number(clubSelectToggle.dataset.clubId) : null;
    if (!clubId) {
      showStatus(statusEl, "Select a club before submitting.", "error");
      return;
    }
    const payload = {
      title,
      description,
      event_type: "event",
      starts_at: buildDateTime(date, startTime),
      ends_at: rrule ? null : buildDateTime(date, endTime),
      rrule,
      duration_minutes: rrule ? durationMinutes : null,
      timezone: calendarTimeZone,
      club_id: clubId,
      room_code: roomCode || null
    };

    try {
      const res = await fetch("/api/calendar/events", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders()
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("create failed");
      showStatus(statusEl, "Submitted for approval.", "success");
      clubEventForm.reset();
      const clubPortal = document.querySelector('[data-portal="club"]');
      if (clubPortal) activateCalendars(clubPortal);
      await loadClubRequests();
    } catch (err) {
      showStatus(statusEl, "Could not submit. Check permissions.", "error");
    }
  });
}

const clubMemberForm = document.getElementById("club-member-form");
if (clubMemberForm) {
  clubMemberForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const statusEl = document.getElementById("club-member-status");
    const formData = new FormData(clubMemberForm);
    const memberEmail = String(formData.get("member_email") || "").trim();
    const clubName = clubSelectToggle ? clubSelectToggle.dataset.clubName : "";

    if (!clubName) {
      showStatus(statusEl, "Select a club first.", "error");
      return;
    }
    if (!memberEmail) {
      showStatus(statusEl, "Email is required.", "error");
      return;
    }

    try {
      const res = await fetch("/api/clubs/members", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders()
        },
        body: JSON.stringify({ club_name: clubName, user_email: memberEmail })
      });
      if (!res.ok) throw new Error("add failed");
      showStatus(statusEl, "Member added.", "success");
      clubMemberForm.reset();
      await loadClubMembers();
    } catch (err) {
      showStatus(statusEl, "Failed to add member.", "error");
    }
  });
}

const adminEventForm = document.getElementById("admin-event-form");
if (adminEventForm) {
  adminEventForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const statusEl = document.getElementById("admin-event-status");

    const formData = new FormData(adminEventForm);
    const title = String(formData.get("title") || "").trim();
    const eventType = String(formData.get("event_type") || "lesson");
    const date = String(formData.get("date") || "").trim();
    const startTime = String(formData.get("start_time") || "").trim();
    const endTime = String(formData.get("end_time") || "").trim();
    const repeat = String(formData.get("repeat") || "none");
    const repeatUntil = String(formData.get("repeat_until") || "").trim();
    const roomCode = String(formData.get("room_code") || "").trim();
    const description = String(formData.get("description") || "").trim();
    const participantsRaw = String(formData.get("participant_ids") || "").trim();

    if (!title || !date || !startTime || !endTime) {
      showStatus(statusEl, "Fill in title, date, and time.", "error");
      return;
    }

    const durationMinutes = diffMinutes(startTime, endTime);
    if (durationMinutes <= 0) {
      showStatus(statusEl, "End time must be after start time.", "error");
      return;
    }

    const rrule = buildRRule(repeat, repeatUntil);
    const participantIds = participantsRaw
      ? participantsRaw
          .split(",")
          .map((value) => Number(value.trim()))
          .filter((value) => !Number.isNaN(value))
      : null;

    const payload = {
      title,
      description,
      event_type: eventType,
      starts_at: buildDateTime(date, startTime),
      ends_at: rrule ? null : buildDateTime(date, endTime),
      rrule,
      duration_minutes: rrule ? durationMinutes : null,
      timezone: calendarTimeZone,
      room_code: roomCode || null,
      participant_ids: participantIds
    };

    try {
      const res = await fetch("/api/calendar/events", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders()
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("create failed");
      showStatus(statusEl, "Created successfully.", "success");
      adminEventForm.reset();
      const adminPortal = document.querySelector('[data-portal="administration"]');
      if (adminPortal) activateCalendars(adminPortal);
      await loadAdminApprovals();
    } catch (err) {
      showStatus(statusEl, "Could not create event.", "error");
    }
  });
}

const adminRoleForm = document.getElementById("admin-role-form");
if (adminRoleForm) {
  adminRoleForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const statusEl = document.getElementById("admin-role-status");
    const formData = new FormData(adminRoleForm);
    const userEmail = String(formData.get("user_email") || "").trim();
    const role = formData.get("role");

    if (!userEmail) {
      showStatus(statusEl, "User email is required.", "error");
      return;
    }

    try {
      const res = await fetch("/api/admin/users/role", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders()
        },
        body: JSON.stringify({ email: userEmail, role })
      });
      if (!res.ok) throw new Error("assign failed");
      showStatus(statusEl, "Role updated.", "success");
    } catch (err) {
      showStatus(statusEl, "Failed to update role.", "error");
    }
  });
}

const adminRoomsList = document.getElementById("admin-rooms-list");
if (adminRoomsList) {
  adminRoomsList.addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-action]");
    if (!btn) return;
    const action = btn.dataset.action;
    const code = btn.dataset.code;
    if (!code) return;
    const room = adminRoomsByCode.get(code);
    if (!room) return;

    if (action === "edit-room") {
      const form = document.getElementById("admin-room-form");
      if (!form) return;
      form.querySelector('input[name="code"]').value = room.code || "";
      form.querySelector('input[name="building"]').value = room.building || "";
      form.querySelector('input[name="floor"]').value = room.floor || "";
      form.querySelector('input[name="room_type"]').value = room.room_type || "";
      form.querySelector('input[name="capacity"]').value = room.capacity || "";
      form.querySelector('select[name="is_active"]').value = room.is_active ? "true" : "false";
      form.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }

    if (action === "delete-room") {
      const statusEl = document.getElementById("admin-room-status");
      showStatus(statusEl, "Deleting room...", "");
      fetch(`/api/admin/rooms/${encodeURIComponent(code)}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      })
        .then((res) => {
          if (!res.ok) throw new Error("delete failed");
          showStatus(statusEl, "Room deleted.", "success");
          loadAdminRooms();
        })
        .catch(() => {
          showStatus(statusEl, "Failed to delete room.", "error");
        });
    }
  });
}

const adminRoomForm = document.getElementById("admin-room-form");
if (adminRoomForm) {
  adminRoomForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const statusEl = document.getElementById("admin-room-status");
    const formData = new FormData(adminRoomForm);
    const code = String(formData.get("code") || "").trim();
    const building = String(formData.get("building") || "").trim();
    const floor = String(formData.get("floor") || "").trim();
    const roomType = String(formData.get("room_type") || "").trim();
    const capacityRaw = String(formData.get("capacity") || "").trim();
    const isActive = String(formData.get("is_active") || "true") === "true";

    if (!code) {
      showStatus(statusEl, "Room code is required.", "error");
      return;
    }

    const capacity = capacityRaw ? Number(capacityRaw) : null;
    if (capacityRaw && Number.isNaN(capacity)) {
      showStatus(statusEl, "Capacity must be a number.", "error");
      return;
    }

    const payload = {
      building: building || null,
      floor: floor || null,
      room_type: roomType || null,
      capacity,
      is_active: isActive
    };

    try {
      let res;
      if (adminRoomsByCode.has(code)) {
        res = await fetch(`/api/admin/rooms/${encodeURIComponent(code)}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            ...getAuthHeaders()
          },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch("/api/admin/rooms", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...getAuthHeaders()
          },
          body: JSON.stringify({ code, ...payload })
        });
      }

      if (!res.ok) throw new Error("room save failed");
      showStatus(statusEl, "Room saved.", "success");
      await loadAdminRooms();
    } catch (err) {
      showStatus(statusEl, "Failed to save room.", "error");
    }
  });
}

const studentClubsList = document.getElementById("student-clubs");
if (studentClubsList) {
  studentClubsList.addEventListener("click", async (event) => {
    const btn = event.target.closest(".club-leave-btn");
    if (!btn) return;
    const clubName = btn.dataset.clubName;
    if (!clubName) return;

    const statusEl = document.getElementById("student-club-status");
    showStatus(statusEl, "Leaving club...", "");
    try {
      const params = new URLSearchParams({ club_name: clubName });
      const res = await fetch(`/api/clubs/members?${params.toString()}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      if (!res.ok) throw new Error("leave failed");
      showStatus(statusEl, "Left club.", "success");
      await loadStudentClubs();
    } catch (err) {
      showStatus(statusEl, "Failed to leave club.", "error");
    }
  });
}

const adminUsersList = document.getElementById("admin-users-list");
if (adminUsersList) {
  adminUsersList.addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-action=\"delete-user\"]");
    if (!btn) return;
    const userId = btn.dataset.id;
    if (!userId) return;
    try {
      const res = await fetch(`/api/admin/users/${userId}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      if (!res.ok) throw new Error("delete failed");
      await loadAdminUsers();
      await loadAdminClubMembers();
      await loadAdminEventParticipants();
      await loadAdminEvents();
    } catch (err) {
      console.warn("Delete user failed", err);
    }
  });
}

const adminClubsList = document.getElementById("admin-clubs-list");
if (adminClubsList) {
  adminClubsList.addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-action=\"delete-club\"]");
    if (!btn) return;
    const clubId = btn.dataset.id;
    if (!clubId) return;
    try {
      const res = await fetch(`/api/admin/clubs/${clubId}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      if (!res.ok) throw new Error("delete failed");
      await loadAdminClubs();
      await loadAdminClubMembers();
      await loadAdminEvents();
    } catch (err) {
      console.warn("Delete club failed", err);
    }
  });
}

const adminClubMembersList = document.getElementById("admin-club-members-list");
if (adminClubMembersList) {
  adminClubMembersList.addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-action=\"delete-club-member\"]");
    if (!btn) return;
    const clubId = btn.dataset.clubId;
    const userId = btn.dataset.userId;
    if (!clubId || !userId) return;
    try {
      const params = new URLSearchParams({ club_id: clubId, user_id: userId });
      const res = await fetch(`/api/admin/club-members?${params.toString()}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      if (!res.ok) throw new Error("delete failed");
      await loadAdminClubMembers();
    } catch (err) {
      console.warn("Delete club member failed", err);
    }
  });
}

const adminEventsList = document.getElementById("admin-events-list");
if (adminEventsList) {
  adminEventsList.addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-action=\"delete-event\"]");
    if (!btn) return;
    const eventId = btn.dataset.id;
    if (!eventId) return;
    try {
      const res = await fetch(`/api/admin/events/${eventId}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      if (!res.ok) throw new Error("delete failed");
      await loadAdminEvents();
      await loadAdminEventParticipants();
      await loadAdminApprovals();
      const adminPortal = document.querySelector('[data-portal="administration"]');
      if (adminPortal) activateCalendars(adminPortal);
    } catch (err) {
      console.warn("Delete event failed", err);
    }
  });
}

const adminParticipantsList = document.getElementById("admin-event-participants-list");
if (adminParticipantsList) {
  adminParticipantsList.addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-action=\"delete-event-participant\"]");
    if (!btn) return;
    const eventId = btn.dataset.eventId;
    const userId = btn.dataset.userId;
    if (!eventId || !userId) return;
    try {
      const params = new URLSearchParams({ event_id: eventId, user_id: userId });
      const res = await fetch(`/api/admin/event-participants?${params.toString()}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      if (!res.ok) throw new Error("delete failed");
      await loadAdminEventParticipants();
    } catch (err) {
      console.warn("Delete event participant failed", err);
    }
  });
}

const adminClubForm = document.getElementById("admin-club-form");
if (adminClubForm) {
  adminClubForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const statusEl = document.getElementById("admin-club-status");
    const formData = new FormData(adminClubForm);
    const name = String(formData.get("name") || "").trim();
    const ownerEmail = String(formData.get("owner_email") || "").trim();

    try {
      const res = await fetch("/api/admin/clubs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          name,
          owner_email: ownerEmail || null
        })
      });
      if (!res.ok) throw new Error("create failed");
      showStatus(statusEl, "Club created.", "success");
      adminClubForm.reset();
    } catch (err) {
      showStatus(statusEl, "Failed to create club.", "error");
    }
  });
}

const adminLeaderForm = document.getElementById("admin-leader-form");
if (adminLeaderForm) {
  adminLeaderForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const statusEl = document.getElementById("admin-leader-status");
    const formData = new FormData(adminLeaderForm);
    const clubName = String(formData.get("club_name") || "").trim();
    const userEmail = String(formData.get("user_email") || "").trim();

    if (!clubName || !userEmail) {
      showStatus(statusEl, "Club name and user email are required.", "error");
      return;
    }

    try {
      const res = await fetch("/api/admin/clubs/leader", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders()
        },
        body: JSON.stringify({ club_name: clubName, user_email: userEmail })
      });
      if (!res.ok) throw new Error("assign failed");
      showStatus(statusEl, "Leader assigned.", "success");
    } catch (err) {
      showStatus(statusEl, "Failed to assign leader.", "error");
    }
  });
}

// --------- UI shortcuts ----------
const newEventButtons = document.querySelectorAll("[data-scroll-target]");
newEventButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const targetId = btn.dataset.scrollTarget;
    const portal = btn.closest('[data-portal="club"]');
    if (portal) {
      const firstTab = portal.querySelector(".student-tabs .tab");
      if (firstTab) firstTab.click();
    }
    if (targetId) {
      const target = document.getElementById(targetId);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
});

document.addEventListener("click", (event) => {
  const btn = event.target.closest(".reserve-room-btn[data-room-code]");
  if (!btn) return;
  const roomCode = btn.dataset.roomCode;
  const portal = btn.closest('[data-portal="club"]');
  if (portal) {
    const firstTab = portal.querySelector(".student-tabs .tab");
    if (firstTab) firstTab.click();
  }
  const form = document.getElementById("club-event-form");
  if (form) {
    const input = form.querySelector('input[name="room_code"]');
    if (input) input.value = roomCode;
    form.scrollIntoView({ behavior: "smooth", block: "start" });
  }
});

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootstrapAuth);
} else {
  bootstrapAuth();
}
