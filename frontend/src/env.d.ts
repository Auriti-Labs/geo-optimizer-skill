/// <reference types="astro/client" />

/**
 * Engine version injected at build time by astro.config.mjs, read from
 * pyproject.toml so the UI badges track the package actually installed.
 */
declare const __ENGINE_VERSION__: string;
