import {
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  Output,
  signal,
} from '@angular/core';

export interface FieldSelectOption {
  value: string;
  label: string;
}

@Component({
  selector: 'app-field-select',
  imports: [],
  templateUrl: './field-select.html',
  styleUrl: './field-select.scss',
})
export class FieldSelect {
  @Input() options: FieldSelectOption[] = [];
  @Input() value = '';
  @Output() valueChange = new EventEmitter<string>();
  @Input() ariaLabel = '';
  @Input() placeholder = 'Select…';

  open = signal(false);
  activeIndex = signal(-1);
  dropUp = signal(false);

  constructor(private host: ElementRef<HTMLElement>) {}

  get selectedLabel(): string {
    const opt = this.options.find((o) => o.value === this.value);
    return opt?.label ?? this.placeholder;
  }

  toggle() {
    if (this.open()) {
      this.close();
    } else {
      this.openPanel();
    }
  }

  openPanel() {
    const trigger = this.host.nativeElement.querySelector('.trigger') as HTMLElement | null;
    if (trigger) {
      const rect = trigger.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      const panelEstimate = 336;
      this.dropUp.set(spaceBelow < panelEstimate && spaceAbove > spaceBelow);
    }
    this.open.set(true);
    const idx = this.options.findIndex((o) => o.value === this.value);
    this.activeIndex.set(idx >= 0 ? idx : 0);
  }

  close() {
    this.open.set(false);
    this.activeIndex.set(-1);
  }

  select(opt: FieldSelectOption) {
    this.value = opt.value;
    this.valueChange.emit(opt.value);
    this.close();
  }

  trackValue = (_: number, opt: FieldSelectOption) => opt.value;

  @HostListener('document:click', ['$event'])
  onDocClick(e: MouseEvent) {
    if (!this.host.nativeElement.contains(e.target as Node)) {
      this.close();
    }
  }

  @HostListener('keydown', ['$event'])
  onKeydown(e: KeyboardEvent) {
    if (!this.open()) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault();
        this.openPanel();
      }
      return;
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      this.close();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      const next = Math.min(this.activeIndex() + 1, this.options.length - 1);
      this.activeIndex.set(next);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const next = Math.max(this.activeIndex() - 1, 0);
      this.activeIndex.set(next);
    } else if (e.key === 'Home') {
      e.preventDefault();
      this.activeIndex.set(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      this.activeIndex.set(this.options.length - 1);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const opt = this.options[this.activeIndex()];
      if (opt) this.select(opt);
    }
  }
}
