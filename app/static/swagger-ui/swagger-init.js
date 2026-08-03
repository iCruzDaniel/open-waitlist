// Swagger UI initializer — kept as an external file (instead of an inline
// <script> in the docs HTML) so the Content-Security-Policy header
// (script-src 'self') can stay strict.
window.onload = function () {
  window.ui = SwaggerUIBundle({
    url: "/openapi.json",
    dom_id: "#swagger-ui",
    deepLinking: true,
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
    layout: "StandaloneLayout",
  });
};
