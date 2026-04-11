import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RestaurantService, Restaurant } from '../../services/restaurant';
import { RestaurantCard } from '../restaurant-card/restaurant-card';

@Component({
  selector: 'app-search',
  imports: [FormsModule, RestaurantCard],
  templateUrl: './search.html',
  styleUrl: './search.scss',
})
export class Search {
  zipCode = '';
  restaurants = signal<Restaurant[]>([]);
  loading = signal(false);
  error = signal('');

  constructor(private restaurantService: RestaurantService) {}

  search() {
    if (!this.zipCode.match(/^\d{4}$/)) {
      this.error.set('Please enter a valid 4-digit Austrian zip code.');
      return;
    }
    this.error.set('');
    this.loading.set(true);
    this.restaurants.set([]);

    this.restaurantService.getRestaurants(this.zipCode).subscribe({
      next: (res) => {
        this.restaurants.set(res.restaurants);
        this.loading.set(false);
        if (res.restaurants.length === 0) {
          this.error.set('No restaurants found for this zip code.');
        }
      },
      error: () => {
        this.error.set('Failed to fetch restaurants. Is the backend running?');
        this.loading.set(false);
      },
    });
  }
}
