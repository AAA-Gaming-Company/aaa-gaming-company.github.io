function nav_bar_expand() {
	var main_bar = document.getElementById("header-right");
	if (main_bar.className == "header-right") {
		main_bar.className = "header-right responsive";
	} else {
		main_bar.className = "header-right";
	}
}