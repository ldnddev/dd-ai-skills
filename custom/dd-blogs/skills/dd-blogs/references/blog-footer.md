  <footer id="footer" hx-trigger="load" hx-get="/includes/footer.html" hx-swap="outerHTML"></footer>

    <script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js"></script>
    <script src="/assets/js/main.js" crossorigin="anonymous" defer></script>
    <script>
      (function () {
        var host = location.hostname;
        var isLocal =
          host === "localhost" ||
          host === "127.0.0.1" ||
          host === "wwwldnddevcom.lndo.site" ||
          host.endsWith(".lndo.site") ||
          host === "172.20.0.2";

        if (!isLocal) return;

        // Keep order: axe-core first, then dd-axe
        function load(src, onload) {
          var s = document.createElement("script");
          s.src = src;
          if (onload) s.onload = onload;
          document.body.appendChild(s);
        }

        load("/assets/vendors/axe/axe.min.js", function () {
          load("/assets/vendors/axe/dd-axe.js");
        });
      })();
    </script>
