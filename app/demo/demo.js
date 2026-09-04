// Demo form logic for the waitlist landing form. Served as an external,
// same-origin script so it complies with the strict Content-Security-Policy
// (script-src 'self') set by SecurityHeadersMiddleware — inline scripts are
// blocked. The waitlist slug is injected by the server into the <body
// data-slug="..."> attribute.
const SLUG = document.body.dataset.slug || "demo";

const EMAIL_DOMAINS = ["gmail.com", "outlook.com", "proton.me", "hey.com", "company.io", "startup.dev"];
const FIRST = ["Ana", "Luis", "María", "Carlos", "Elena", "Jorge", "Lucía", "Diego", "Sofía", "Andrés", "Valentina", "Mateo"];
const LAST = ["García", "Rodríguez", "Martínez", "López", "Hernández", "González", "Pérez", "Sánchez", "Ramírez", "Torres", "Flores", "Rivera"];
const COMPANIES = ["Acme", "Globex", "Initech", "Umbrella", "Stark", "Wayne", "Hooli", "Pied Piper", "Nimbus", "Brightpath", "Cloudline", "Atomica"];
const REFERRERS = ["twitter", "linkedin", "google", "facebook", "instagram", "friend", "newsletter", "podcast"];

function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

function randomEmail(name) {
  const base = name.toLowerCase().replace(/[^a-z]/g, "").slice(0, 8);
  return base + Math.floor(100 + Math.random() * 900) + "@" + pick(EMAIL_DOMAINS);
}

function randomData() {
  const first = pick(FIRST);
  const last = pick(LAST);
  const name = first + " " + last;
  const email = randomEmail(first + last);
  const company = pick(COMPANIES);
  const role = pick(["Founder", "Engineer", "Product Manager", "Marketer", "Designer", "CTO"]);
  return { name, email, company, role, referrer: pick(REFERRERS) };
}

function fillForm() {
  const d = randomData();
  document.getElementById("name").value = d.name;
  document.getElementById("email").value = d.email;
  document.getElementById("company").value = d.company + " · " + d.role;
  document.getElementById("msg").textContent = "";
  document.getElementById("msg").className = "msg";
}

document.getElementById("fill-btn").addEventListener("click", fillForm);

document.getElementById("lead-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("submit-btn");
  const msg = document.getElementById("msg");
  btn.disabled = true;
  msg.textContent = "Submitting…";
  msg.className = "msg";

  const data = {
    name: document.getElementById("name").value,
    email: document.getElementById("email").value,
    company: document.getElementById("company").value,
  };
  if (data.email) data.referrer = "demo-form";

  try {
    const res = await fetch("/waitlists/" + SLUG + "/entries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      msg.textContent = "Error: " + (body.detail || res.statusText);
      msg.className = "msg err";
      return;
    }
    msg.textContent = "🎉 You're on the list! Check the admin panel.";
    msg.className = "msg ok";
    document.getElementById("lead-form").reset();
  } catch (err) {
    msg.textContent = "Network error: " + err.message;
    msg.className = "msg err";
  } finally {
    btn.disabled = false;
  }
});
