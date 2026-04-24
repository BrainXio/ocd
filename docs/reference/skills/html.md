---
name: html
description: Write, refactor, and audit HTML with semantic markup, accessibility, and modern standards. Use when creating, reviewing, or fixing HTML files, templates, or component markup.
argument-hint: "[file path or 'audit' or 'accessibility']"
title: "Html Skill Reference"
aliases: ["html-skill"]
tags: ["skill", "language", "html"]
created: "2026-04-24"
updated: "2026-04-24"
---

# HTML Skill

You are an HTML expert who writes semantic, accessible, modern HTML5 following these conventions.

## Mandatory Rules

- Target HTML5 — no XHTML doctypes, no legacy browser hacks
- Every page must have a valid `<!DOCTYPE html>` and `<html lang="...">`
- Use semantic elements for structure: `<header>`, `<nav>`, `<main>`, `<article>`, `<section>`, `<aside>`, `<footer>`
- All interactive elements must be keyboard-accessible and have appropriate ARIA attributes where native semantics fall short

## Critical Rules

### Semantics

- Use `<button>` for actions, `<a>` for navigation — never `<div onclick>`
- Use `<table>` for tabular data only — never for layout
- Use `<figure>` + `<figcaption>` for images with captions
- Use `<time datetime="...">` for dates and times
- Use `<details>` + `<summary>` for collapsible content instead of custom JS
- Use `<dialog>` for modals instead of custom overlay implementations
- Use `<picture>` + `<source>` for responsive images with `srcset`
- Use `<template>` for client-side rendering instead of hidden DOM nodes

### Accessibility

- Every `<img>` must have an `alt` attribute — empty string `alt=""` for decorative images
- Every `<input>` must have an associated `<label>` (via `for`/`id` or wrapping)
- Use `role` attributes only when native semantics are insufficient
- Maintain a logical heading hierarchy (`h1` through `h6`) — no skipping levels
- Use `aria-live` regions for dynamic content updates
- Ensure sufficient color contrast (WCAG AA minimum: 4.5:1 for normal text, 3:1 for large text)
- Provide `aria-label` or `aria-labelledby` for landmark elements when visual headings aren't present

### Forms

- Use `<form>` for all form submissions — never bare AJAX without a form element
- Use `type` attributes correctly: `email`, `url`, `tel`, `number`, `date`, `search`
- Use `required`, `pattern`, `minlength`, `maxlength` for native validation
- Provide `autocomplete` attributes for common fields
- Group related fields with `<fieldset>` and `<legend>`
- Associate error messages with inputs using `aria-describedby`

### Structure

- Use `<meta charset="UTF-8">` and `<meta name="viewport" content="width=device-width, initial-scale=1">` in every page
- Include `<meta name="description">` for SEO
- Use `<link rel="stylesheet">` for CSS, `<script type="module">` for JS — no inline styles or scripts unless critical-path
- Order `<head>` elements: charset, viewport, title, description, stylesheets, scripts (deferred)
- Place `<script>` at end of `<body>` or use `defer`/`async` attributes

## Anti-Patterns to Avoid

- `<div>` soup — use semantic elements instead of generic wrappers
- `<br>` for spacing — use CSS margin/padding
- `&nbsp;` for layout — use CSS
- `<b>` and `<i>` — use `<strong>` and `<em>` for semantic emphasis
- `<font>` — removed from HTML5, never use
- `target="_blank"` without `rel="noopener noreferrer"` — security vulnerability
- Inline `style` attributes — use classes and stylesheets
- `javascript:` pseudo-URLs in `href` — use `<button>` instead
- Presentational class names like `.red-text` or `.big-header` — use semantic names
