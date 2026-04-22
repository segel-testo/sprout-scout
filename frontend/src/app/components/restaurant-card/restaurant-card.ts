import { Component, Input, OnChanges, signal } from '@angular/core';
import { Restaurant, RestaurantService, ScanResult } from '../../services/restaurant';

@Component({
  selector: 'app-restaurant-card',
  imports: [],
  templateUrl: './restaurant-card.html',
  styleUrl: './restaurant-card.scss',
})
export class RestaurantCard implements OnChanges {
  @Input() restaurant!: Restaurant;
  @Input() prescan: ScanResult | null = null;

  expanded = signal(false);
  scan = signal<ScanResult | null>(null);
  loading = signal(false);
  scanned = signal(false);

  constructor(private restaurantService: RestaurantService) {}

  ngOnChanges(): void {
    if (this.prescan) {
      this.scan.set(this.prescan);
      this.scanned.set(true);
      this.expanded.set(true);
    }
  }

  toggle() {
    this.expanded.set(!this.expanded());
    if (this.expanded() && !this.scanned()) {
      this.loading.set(true);
      this.restaurantService.getVeganDishes(this.restaurant).subscribe({
        next: (res) => {
          this.scan.set(res);
          this.loading.set(false);
          this.scanned.set(true);
        },
        error: () => {
          this.loading.set(false);
          this.scanned.set(true);
        },
      });
    }
  }

  confidenceLabel(score: number): string {
    if (score >= 0.8) return 'high';
    if (score >= 0.6) return 'medium';
    return 'low';
  }

  dietHintLabel(hint: string | null | undefined): string | null {
    switch (hint) {
      case 'only': return 'OpenStreetMap: fully vegan restaurant';
      case 'yes': return 'OpenStreetMap: has vegan options';
      case 'limited': return 'OpenStreetMap: limited vegan options';
      default: return null;
    }
  }
}
