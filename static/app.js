const socket = io();
const fileList = document.getElementById("fileList");
const pendingList = document.getElementById("pendingList");

function refresh() {
  fetch("/api/status")
    .then((res) => res.json())
    .then((data) => {
      pendingList.innerHTML = "";
      data.pending.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = `${item.type.toUpperCase()} → ${item.src}`;
        pendingList.appendChild(li);
      });

      fileList.innerHTML = "";
      data.files.forEach((file) => {
        const li = document.createElement("li");
        li.innerHTML = `<span>${file.path}</span> <span class="status">${new Date(file.mtime * 1000).toLocaleString()}</span>`;
        fileList.appendChild(li);
      });
    });
}

document.getElementById("pullBtn").onclick = () => {
  fetch("/api/pull", { method: "POST" })
    .then((res) => res.json())
    .then((d) => {
      alert(d.status === "ok" ? "Pulled from cloud." : "Pull failed.");
      refresh();
    });
};

document.getElementById("pushBtn").onclick = () => {
  fetch("/api/push", { method: "POST" })
    .then((res) => res.json())
    .then((d) => {
      alert(d.status === "ok" ? "Changes pushed." : d.message || "Push failed.");
      refresh();
    });
};

socket.on("change", (data) => {
  refresh();
});

refresh();
