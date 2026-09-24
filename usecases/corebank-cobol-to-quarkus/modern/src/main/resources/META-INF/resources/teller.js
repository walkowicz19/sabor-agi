const screen = document.querySelector("#screen");
const title = document.querySelector("#title");
const alertBox = document.querySelector("#alert");

let token = "";

const screens = {
  signon: renderSignOn,
  menu: renderMenu,
  register: renderRegister,
  inquiry: renderInquiry,
  pin: renderPin,
};

show("signon");

function show(name, extra) {
  clearAlert();
  title.textContent = {
    signon: "Sign on",
    menu: "Teller menu",
    register: "Register customer",
    inquiry: "Inquiry",
    pin: "Change PIN",
  }[name];
  screen.replaceChildren();
  screens[name](extra);
}

function clearAlert() {
  alertBox.hidden = true;
  alertBox.textContent = "";
}

function fail(message) {
  alertBox.hidden = false;
  alertBox.textContent = message;
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("X-Operator-Token", token);
  }
  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }
  if (!response.ok) {
    throw new Error(payload && payload.error ? payload.error : "The desk could not complete that.");
  }
  return payload;
}

function field(label, name, options) {
  const wrap = document.createElement("label");
  wrap.textContent = label;
  const input = document.createElement("input");
  input.name = name;
  input.required = true;
  input.autocomplete = "off";
  input.inputMode = "numeric";
  input.maxLength = options.length;
  input.pattern = "\\d{" + options.length + "}";
  input.title = options.title;
  if (options.secret) {
    input.type = "password";
  }
  wrap.append(input);
  return wrap;
}

function textField(label, name) {
  const wrap = document.createElement("label");
  wrap.textContent = label;
  const input = document.createElement("input");
  input.name = name;
  input.required = true;
  input.maxLength = 40;
  input.autocomplete = "name";
  wrap.append(input);
  return wrap;
}

function submitButton(label) {
  const button = document.createElement("button");
  button.className = "primary";
  button.type = "submit";
  button.textContent = label;
  return button;
}

function backButton() {
  const button = document.createElement("button");
  button.className = "choice";
  button.type = "button";
  button.textContent = "Back to menu";
  button.addEventListener("click", () => show("menu"));
  return button;
}

async function withBusy(button, pending, work) {
  button.disabled = true;
  const previous = button.textContent;
  button.textContent = pending;
  try {
    await work();
  } catch (error) {
    fail(error.message);
  } finally {
    button.disabled = false;
    button.textContent = previous;
  }
}

function renderSignOn() {
  token = "";
  const form = document.createElement("form");
  form.append(
    field("Operator id", "operatorId", { length: 4, title: "4 digits" }),
    field("Operator PIN", "pin", { length: 6, secret: true, title: "6 digits" }),
    submitButton("Sign on"),
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    clearAlert();
    const data = new FormData(form);
    const button = form.querySelector("button");
    withBusy(button, "Signing on…", async () => {
      const result = await api("/sessions", {
        method: "POST",
        body: JSON.stringify({
          operatorId: data.get("operatorId"),
          pin: data.get("pin"),
        }),
      });
      token = result.token;
      show("menu");
    });
  });
  screen.append(form);
}

function renderMenu() {
  const stack = document.createElement("div");
  stack.className = "stack";
  const actions = [
    ["1", "Register customer", "register"],
    ["2", "Inquiry", "inquiry"],
    ["3", "Change PIN", "pin"],
    ["9", "Exit", "signon"],
  ];
  for (const [code, label, next] of actions) {
    const button = document.createElement("button");
    button.className = "choice";
    button.type = "button";
    const key = document.createElement("kbd");
    key.textContent = code;
    button.append(key, document.createTextNode(label));
    button.addEventListener("click", () => choose(next));
    stack.append(button);
  }
  const hint = document.createElement("p");
  hint.className = "note";
  hint.textContent = "Keys 1, 2, 3, and 9 select an action.";
  stack.append(hint);
  screen.append(stack);
  screen.tabIndex = -1;
  const onKey = (event) => {
    const next = { 1: "register", 2: "inquiry", 3: "pin", 9: "signon" }[event.key];
    if (next) {
      choose(next);
    }
  };
  document.addEventListener("keydown", onKey, { once: false });
  const observer = new MutationObserver(() => {
    if (!screen.contains(stack)) {
      document.removeEventListener("keydown", onKey);
      observer.disconnect();
    }
  });
  observer.observe(screen, { childList: true });
}

async function choose(next) {
  if (next !== "signon") {
    show(next);
    return;
  }
  const current = token;
  token = "";
  try {
    await fetch("/sessions", { method: "DELETE", headers: { "X-Operator-Token": current } });
  } catch {
    /* The desk still returns to sign-on if the network drops. */
  }
  show("signon");
}

function renderRegister() {
  const form = document.createElement("form");
  form.append(
    field("Customer number", "customerNumber", { length: 10, title: "10 digits" }),
    textField("Name", "name"),
    field("Branch", "branchCode", { length: 4, title: "4 digits" }),
    field("PIN", "pin", { length: 6, secret: true, title: "6 digits" }),
    submitButton("Register"),
    backButton(),
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    clearAlert();
    const data = new FormData(form);
    const button = form.querySelector(".primary");
    withBusy(button, "Registering…", async () => {
      const created = await api("/customers", {
        method: "POST",
        body: JSON.stringify({
          customerNumber: data.get("customerNumber"),
          name: data.get("name"),
          branchCode: data.get("branchCode"),
          pin: data.get("pin"),
        }),
      });
      showRecord(created, "Customer registered. The PIN is not shown again.");
    });
  });
  screen.append(form);
}

function renderInquiry() {
  const form = document.createElement("form");
  form.append(
    field("Customer number", "customerNumber", { length: 10, title: "10 digits" }),
    submitButton("Look up"),
    backButton(),
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    clearAlert();
    const number = new FormData(form).get("customerNumber");
    const button = form.querySelector(".primary");
    withBusy(button, "Looking up…", async () => {
      const found = await api("/customers/" + encodeURIComponent(number));
      showRecord(found, "Inquiry does not include the PIN.");
    });
  });
  screen.append(form);
}

function renderPin() {
  const form = document.createElement("form");
  form.append(
    field("Customer number", "customerNumber", { length: 10, title: "10 digits" }),
    field("Current PIN", "oldPin", { length: 6, secret: true, title: "6 digits" }),
    field("New PIN", "newPin", { length: 6, secret: true, title: "6 digits" }),
    submitButton("Update PIN"),
    backButton(),
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    clearAlert();
    const data = new FormData(form);
    const button = form.querySelector(".primary");
    withBusy(button, "Updating…", async () => {
      await api("/customers/" + encodeURIComponent(data.get("customerNumber")) + "/pin", {
        method: "POST",
        body: JSON.stringify({ oldPin: data.get("oldPin"), newPin: data.get("newPin") }),
      });
      clearAlert();
      const note = document.createElement("p");
      note.className = "note";
      note.textContent = "PIN updated. It is stored as a hash and is not shown here.";
      form.reset();
      form.before(note);
    });
  });
  screen.append(form);
}

function showRecord(customer, noteText) {
  screen.replaceChildren();
  title.textContent = "Customer";
  const list = document.createElement("dl");
  list.className = "record";
  for (const [label, value] of [
    ["Number", customer.customerNumber],
    ["Name", customer.name],
    ["Branch", customer.branchCode],
    ["Balance", formatBalance(customer.balance)],
    ["Status", customer.status],
  ]) {
    const row = document.createElement("div");
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = value;
    row.append(dt, dd);
    list.append(row);
  }
  const note = document.createElement("p");
  note.className = "note";
  note.textContent = noteText;
  screen.append(list, note, backButton());
}

function formatBalance(value) {
  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return String(value);
  }
  return amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
