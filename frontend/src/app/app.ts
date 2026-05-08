import { Component, signal } from '@angular/core';
import { Search } from './components/search/search';
import { LegalKind, LegalModal } from './components/legal-modal/legal-modal';

@Component({
  selector: 'app-root',
  imports: [Search, LegalModal],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  readonly year = new Date().getFullYear();

  legalOpen = signal<LegalKind | null>(null);

  openLegal(kind: LegalKind) {
    this.legalOpen.set(kind);
  }

  closeLegal() {
    this.legalOpen.set(null);
  }
}
