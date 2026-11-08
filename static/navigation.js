'use strict';

// Private page drafts stay in this tab's memory. Browser history receives opaque IDs only.
class NavigationTrail {
  constructor(history, namespace) {
    this.history = history;
    this.namespace = namespace;
    this.pages = new Map();
    this.current = null;
    this.sequence = 0;
  }
  visit(key, data) {
    if (this.current && this.pages.get(this.current)?.key === key) {
      this.update(data);
      return;
    }
    const id = `${this.namespace}:${++this.sequence}`;
    this.pages.set(id, {key, data: structuredClone(data), previous: this.current});
    const method = this.current ? 'pushState' : 'replaceState';
    this.current = id;
    this.history[method]({firstvisitRoute: id}, '');
    if (this.pages.size > 40) this.pages.delete(this.pages.keys().next().value);
  }
  update(data) {
    const page = this.pages.get(this.current);
    if (page) page.data = structuredClone(data);
  }
  restore(id) {
    const page = this.pages.get(id);
    if (!page) return null;
    this.current = id;
    return structuredClone(page.data);
  }
  get canGoBack() {
    return !!this.pages.get(this.pages.get(this.current)?.previous);
  }
  clear() {
    this.pages.clear();
    this.current = null;
  }
}
if (typeof module !== 'undefined') module.exports = {NavigationTrail};
