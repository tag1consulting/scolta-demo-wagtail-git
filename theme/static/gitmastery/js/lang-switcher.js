/* Collapsible language switcher for narrow viewports.
 * Adapted from the Drupal gitmastery_theme lang-switcher.js for this markup
 * (.language-switcher > ul.language-switcher__list with the active <li>).
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var block = document.querySelector('.language-switcher');
    if (!block) { return; }

    var list = block.querySelector('.language-switcher__list');
    if (!list) { return; }

    var activeItem = list.querySelector('li.is-active');
    var activeLink = activeItem ? activeItem.querySelector('a') : null;
    if (!activeLink) { return; }

    // In-flow trigger showing the active 2-letter code; the panel stays absolute.
    var trigger = document.createElement('button');
    trigger.className = 'lang-trigger';
    trigger.setAttribute('type', 'button');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.textContent = activeLink.textContent.trim();
    list.parentNode.insertBefore(trigger, list);

    function close() { block.classList.remove('is-open'); trigger.setAttribute('aria-expanded', 'false'); }
    function open() { block.classList.add('is-open'); trigger.setAttribute('aria-expanded', 'true'); }

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      block.classList.contains('is-open') ? close() : open();
    });
    document.addEventListener('click', function (e) { if (!block.contains(e.target)) { close(); } });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { close(); } });
  });
}());
