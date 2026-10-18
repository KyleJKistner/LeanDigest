"use strict";
(() => {
  const data = JSON.parse(document.getElementById("companion-data").textContent);
  const byId = id => document.getElementById(id);
  const sections = new Map(data.sections.map(section => [section.id, section]));
  const frames = new Map(data.snapshot.frames.map(frame => [frame.id, frame]));
  const dialog = byId("evidence-dialog");
  let opener = null;
  let activeSection = sections.get("statement");
  let toastTimer;

  function renderMath(root = document) {
    root.querySelectorAll("[data-math]").forEach(element => {
      // Native MathML needs no downloaded fonts, stylesheet, or remote renderer.
      katex.render(element.dataset.math, element, {
        displayMode: element.classList.contains("math-display"),
        output: "mathml", throwOnError: true, strict: "error", trust: false,
      });
    });
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function math(expression, className = "math-display") {
    const node = element("div", className, expression);
    node.dataset.math = expression;
    return node;
  }

  function setFrame(id) {
    const frame = frames.get(Number(id));
    if (!frame || !activeSection.frames.includes(frame.id)) return;
    byId("frame-select").value = String(frame.id);
    byId("frame-role").textContent = `Frame f${frame.id} · role: ${frame.role}${frame.head ? ` · head: ${frame.head}` : ""}`;
    byId("frame-statement").textContent = frame.statement;
    const hasDomain = typeof frame.domain === "string";
    byId("frame-domain-section").hidden = !hasDomain;
    if (hasDomain) {
      byId("frame-domain-label").textContent = frame.role === "define" ? "Introduced object and type" : "Introduced binder and type or claim";
      byId("frame-domain").textContent = `${frame.binder || "(unnamed)"} : ${frame.domain}${frame.value === undefined ? "" : `\n:= ${frame.value}`}`;
    }
    byId("frame-context").textContent = frame.context.length
      ? frame.context.map(item => `${item.name} : ${item.type}`).join("\n")
      : "(empty local context)";
    byId("frame-raw").textContent = JSON.stringify(frame, null, 2);
  }

  function setSource(section) {
    const container = byId("dialog-source");
    container.replaceChildren();
    data.original_source.split("\n").forEach((line, index) => {
      const number = index + 1;
      const row = element("span", "source-line");
      row.dataset.line = String(number);
      if (number >= section.lines[0] && number <= section.lines[1]) row.classList.add("highlighted");
      const label = element("span", "source-number", String(number));
      label.setAttribute("aria-hidden", "true");
      row.append(label, element("span", "source-code", line));
      container.append(row);
    });
  }

  function scrollSource() {
    requestAnimationFrame(() => {
      const source = byId("dialog-source");
      const first = source.querySelector(".highlighted");
      if (first && !byId("evidence-panel-source").hidden) {
        source.scrollTop = Math.max(0, first.offsetTop - source.offsetTop - 25);
        source.scrollLeft = 0;
      }
    });
  }

  function setEvidenceView(view, focus = false) {
    if (!["source", "frames", "receipt"].includes(view)) view = "source";
    document.querySelectorAll("[data-evidence-view]").forEach(tab => {
      const selected = tab.dataset.evidenceView === view;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      byId(tab.getAttribute("aria-controls")).hidden = !selected;
      if (selected && focus) tab.focus();
    });
    if (view === "source") scrollSource();
  }

  function inspect(sectionId, view, button) {
    activeSection = sections.get(sectionId) || sections.get("statement");
    opener = button;
    byId("evidence-dialog-title").textContent = activeSection.title;
    byId("evidence-dialog-note").textContent = `Original source, lines ${activeSection.lines.join("–")} · ${activeSection.frames.length} recorded frames in this editorial group · source mapping is not formal English certification.`;
    setSource(activeSection);
    const options = activeSection.frames.map(id => {
      const frame = frames.get(id);
      const option = element("option", "", `f${id} · ${frame.role}${frame.head ? ` · ${frame.head}` : ""}`);
      option.value = String(id);
      return option;
    });
    byId("frame-select").replaceChildren(...options);
    setFrame(activeSection.focus);
    setEvidenceView(view);
    dialog.showModal();
    byId(`evidence-tab-${view || "source"}`).focus({preventScroll: true});
    scrollSource();
  }

  document.querySelectorAll("[data-section]").forEach(button => {
    button.addEventListener("click", () => inspect(button.dataset.section, button.dataset.evidenceTab || "source", button));
  });
  byId("run-record-btn").addEventListener("click", event => inspect("statement", "receipt", event.currentTarget));
  byId("dialog-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => {
    if (opener && opener.isConnected) opener.focus({preventScroll: true});
  });
  byId("frame-select").addEventListener("change", event => setFrame(event.target.value));
  const evidenceTabs = [...document.querySelectorAll("[data-evidence-view]")];
  evidenceTabs.forEach((tab, index) => {
    tab.addEventListener("click", () => setEvidenceView(tab.dataset.evidenceView));
    tab.addEventListener("keydown", event => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % evidenceTabs.length;
      else if (event.key === "ArrowLeft") next = (index + evidenceTabs.length - 1) % evidenceTabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = evidenceTabs.length - 1;
      else return;
      event.preventDefault();
      setEvidenceView(evidenceTabs[next].dataset.evidenceView, true);
    });
  });

  byId("full-source").textContent = data.original_source;
  byId("dialog-receipt").textContent = JSON.stringify({receipt: data.receipt, observation: data.native_record}, null, 2);
  const identityPairs = [
    ["Theorem", data.theorem],
    ["Original file", data.original_source_path],
    ["Original source · SHA-256 of exact bytes", data.original_source_sha256],
    ["Adapted context · SHA-256 of exact bytes", data.context_sha256],
    ["Checking transport · SHA-256 of exact bytes", data.transport_source_sha256],
    ["Selected snapshot · SHA-256 of canonical JSON", data.snapshot_sha256],
    ["Lean version", data.snapshot.lean_version],
    ["Mathlib revision pinned by the OpenAI release", data.native_record.mathlib_commit],
    ["Axioms reported by Lean", data.snapshot.axioms.join(", ")],
    ["Curated prose and source mapping", "Editorially reviewed; not formally certified"],
  ];
  identityPairs.forEach(([label, value]) => byId("identity-list").append(element("dt", "", label), element("dd", "", value)));
  if (data.native_record) {
    byId("native-record-section").hidden = false;
    byId("native-record").textContent = JSON.stringify(data.native_record, null, 2);
  }

  function notify(message) {
    clearTimeout(toastTimer);
    byId("toast").textContent = message;
    byId("toast").hidden = false;
    toastTimer = setTimeout(() => { byId("toast").hidden = true; }, 4500);
  }

  const downloads = {
    source: ["BezoutFrame-original.lean", "text/plain", data.original_source],
    context: ["BezoutFrame-adapted-context.lean", "text/plain", data.context_source],
    transport: ["BezoutFrame-checking-transport.lean", "text/plain", data.transport_source],
    snapshot: ["BezoutFrame-snapshot.json", "application/json", data.snapshot],
    receipt: ["BezoutFrame-receipt.json", "application/json", data.receipt],
    observation: ["BezoutFrame-native-observation.json", "application/json", data.native_record],
    certificates: ["BezoutFrame-polynomial-certificates.json", "application/json", data.certificates],
    reader: ["BezoutFrame-deterministic-reader.html", "text/html", data.deterministic_reader_html],
  };
  document.querySelectorAll("[data-download]").forEach(button => {
    button.addEventListener("click", () => {
      const [name, type, value] = downloads[button.dataset.download];
      const contents = typeof value === "string" ? value : JSON.stringify(value, null, 2) + "\n";
      const url = URL.createObjectURL(new Blob([contents], {type: `${type};charset=utf-8`}));
      const link = element("a");
      link.href = url;
      link.download = name;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      notify(`Prepared ${name}.`);
    });
  });

  // Preset illustrations use BigInt throughout; no floating-point division.
  const examples = {
    ordinary: [12n, 6n, 8n], zero: [0n, 7n, 0n], negative: [-6n, -1n, 2n],
  };
  function bezout(x, z) {
    let oldR = x < 0n ? -x : x, rem = z < 0n ? -z : z;
    let oldS = 1n, s = 0n, oldT = 0n, t = 1n;
    while (rem !== 0n) {
      const q = oldR / rem;
      [oldR, rem] = [rem, oldR - q * rem];
      [oldS, s] = [s, oldS - q * s];
      [oldT, t] = [t, oldT - q * t];
    }
    return [oldR, oldS * (x < 0n ? -1n : 1n), oldT * (z < 0n ? -1n : 1n)];
  }
  const signed = value => value < 0n ? `(${value})` : String(value);
  function showExample(name) {
    const [x, y, z] = examples[name];
    if (x * y !== z * (z + 1n)) throw new Error("Example violates the theorem hypothesis");
    const [g, r, s] = bezout(x, z);
    let a, d, b, c;
    if (g === 0n) [a, d, b, c] = [1n, y, 0n, 1n];
    else {
      [a, d, b, c] = [x / g, z / g, g, r * (z + 1n) + s * y];
      if (x !== g * a || z !== g * d || a * r + d * s !== 1n || a * y !== d * (z + 1n)) {
        throw new Error("Example violates an intermediate relation");
      }
    }
    const conclusions = [a * b === x, d * c === y, d * b === z, a * c - d * b === 1n];
    if (!conclusions.every(Boolean)) throw new Error("Example construction failed");
    const output = byId("example-output");
    output.replaceChildren();
    output.dataset.case = name;
    output.dataset.witnesses = [a, d, b, c].map(String).join(",");
    output.dataset.hypothesisChecked = "true";
    output.append(math(`(x,y,z)=(${x},${y},${z}),\\quad xy=z(z+1)=${x * y}.`, "math-display example-values"));
    const note = element("p", "example-note");
    if (g === 0n) {
      note.textContent = "Here the gcd is zero, so the first branch gives the witnesses directly. There is no cancellation by zero.";
    } else {
      note.append(element("span", "", "The computation chooses "));
      const inline = element("span");
      inline.dataset.math = `g=${g},\\ r=${r},\\ s=${s}`;
      note.append(inline, element("span", "", ". These coefficients satisfy the Bézout identity."));
    }
    output.append(note);
    const witnesses = element("div", "example-witnesses");
    witnesses.append(math(`M=\\begin{pmatrix}${a}&${d}\\\\${b}&${c}\\end{pmatrix}`));
    witnesses.append(math(`(a,d,b,c)=(${a},${d},${b},${c})`, "math-display witness-list"));
    output.append(witnesses);
    const checks = element("div", "example-checks");
    const equations = [
      `ab=${signed(a)}\\cdot${signed(b)}=${x}`,
      `dc=${signed(d)}\\cdot${signed(c)}=${y}`,
      `db=${signed(d)}\\cdot${signed(b)}=${z}`,
      `ac-db=${signed(a * c)}-${signed(d * b)}=1`,
    ];
    equations.forEach((equation, index) => {
      const check = element("div", "example-check");
      check.dataset.checked = String(conclusions[index]);
      const icon = element("span", "check-icon", "✓");
      icon.setAttribute("aria-label", "Verified by exact integer arithmetic:");
      const value = element("span");
      value.dataset.math = equation;
      check.append(icon, value);
      checks.append(check);
    });
    output.append(checks);
    document.querySelectorAll("[data-example]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.example === name)));
    renderMath(output);
  }
  document.querySelectorAll("[data-example]").forEach(button => button.addEventListener("click", () => showExample(button.dataset.example)));
  byId("print-btn").addEventListener("click", () => window.print());

  if ("IntersectionObserver" in window) {
    const outline = [...document.querySelectorAll(".contents li a")];
    const observer = new IntersectionObserver(entries => {
      const visible = entries.filter(entry => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (!visible) return;
      outline.forEach(link => {
        if (link.hash === `#${visible.target.id}`) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    }, {rootMargin: "-5% 0px -65% 0px", threshold: 0});
    document.querySelectorAll(".proof-step").forEach(step => observer.observe(step));
  }
  renderMath();
  showExample("ordinary");
  document.documentElement.dataset.companionReady = "true";
})();
