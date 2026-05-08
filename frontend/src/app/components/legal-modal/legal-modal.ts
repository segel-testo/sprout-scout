import {
  Component,
  EventEmitter,
  HostListener,
  Input,
  Output,
} from '@angular/core';

export type LegalKind = 'impressum' | 'privacy';

@Component({
  selector: 'app-legal-modal',
  imports: [],
  templateUrl: './legal-modal.html',
  styleUrl: './legal-modal.scss',
})
export class LegalModal {
  @Input({ required: true }) kind!: LegalKind;
  @Output() closed = new EventEmitter<void>();

  close() {
    this.closed.emit();
  }

  onBackdrop(e: MouseEvent) {
    if ((e.target as HTMLElement).classList.contains('backdrop')) {
      this.close();
    }
  }

  @HostListener('document:keydown.escape')
  onEscape() {
    this.close();
  }
}
