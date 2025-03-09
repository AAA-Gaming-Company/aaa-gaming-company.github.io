// Redirect to https
if (window.location.protocol != "https:" && window.location.hostname != "localhost") {
  window.location.href = "https:" + window.location.href.substring(window.location.protocol.length);
}

// Set up redirection elements
const redirections = document.querySelectorAll("[data-redirect]");
redirections.forEach(element => {
  const url = element.getAttribute("data-redirect");
  element.removeAttribute("data-redirect");
  element.addEventListener("click", function() {
    window.location.href = url;
  });
});