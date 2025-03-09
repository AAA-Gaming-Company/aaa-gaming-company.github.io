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

// Set up tricolor AAA
const tricolor = document.querySelectorAll("[data-tricolor-a]");
tricolor.forEach(element => {
  element.removeAttribute("data-tricolor-a");
  //Validate old text
  if (element.innerHTML.trim() !== "AAA") {
    console.error("Tricolor element should be empty");
    return;
  }
  element.classList.add("tricolor-a");
  element.innerHTML = `<span>A</span><span>A</span><span>A</span>`;
});