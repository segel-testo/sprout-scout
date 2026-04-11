import { Component, Input, signal } from '@angular/core';
import { Restaurant, VeganDish, RestaurantService } from '../../services/restaurant';

@Component({
  selector: 'app-restaurant-card',
  imports: [],
  templateUrl: './restaurant-card.html',
  styleUrl: './restaurant-card.scss',
})
export class RestaurantCard {
  @Input() restaurant!: Restaurant;

  expanded = signal(false);
  dishes = signal<VeganDish[]>([]);
  loading = signal(false);
  scanned = signal(false);

  constructor(private restaurantService: RestaurantService) {}

  toggle() {
    this.expanded.set(!this.expanded());
    if (this.expanded() && !this.scanned()) {
      this.loading.set(true);
      this.restaurantService.getVeganDishes(this.restaurant.id, this.restaurant.website).subscribe({
        next: (res) => {
          this.dishes.set(res.dishes);
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
}
