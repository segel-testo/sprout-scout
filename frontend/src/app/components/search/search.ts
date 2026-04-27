import { Component, OnDestroy, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { Restaurant, RestaurantService, ScanResult } from '../../services/restaurant';
import { RestaurantCard } from '../restaurant-card/restaurant-card';

interface ListItem {
  restaurant: Restaurant;
  scan: ScanResult;
}

export const AMENITY_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All amenities' },
  { value: 'restaurant', label: 'Restaurant' },
  { value: 'cafe', label: 'Café' },
  { value: 'fast_food', label: 'Fast food' },
  { value: 'pub', label: 'Pub' },
  { value: 'bar', label: 'Bar' },
  { value: 'biergarten', label: 'Biergarten' },
  { value: 'food_court', label: 'Food court' },
  { value: 'ice_cream', label: 'Ice cream' },
];

@Component({
  selector: 'app-search',
  imports: [FormsModule, RestaurantCard],
  templateUrl: './search.html',
  styleUrl: './search.scss',
})
export class Search implements OnDestroy {
  zipCode = '';
  selectedAmenity = '';
  amenityOptions = AMENITY_OPTIONS;
  items = signal<ListItem[]>([]);
  loading = signal(false);
  error = signal('');

  scanProgress = signal<{ scanned: number; total: number } | null>(null);
  scanCapped = signal(false);

  private streamSub?: Subscription;

  constructor(private restaurantService: RestaurantService) {}

  ngOnDestroy(): void {
    this.streamSub?.unsubscribe();
  }

  search() {
    if (!this.zipCode.match(/^\d{4}$/)) {
      this.error.set('Please enter a valid 4-digit Austrian zip code.');
      return;
    }
    this.error.set('');
    this.items.set([]);
    this.scanProgress.set(null);
    this.scanCapped.set(false);
    this.streamSub?.unsubscribe();

    this.loading.set(true);
    this.streamSub = this.restaurantService.scanStream(this.zipCode, this.selectedAmenity).subscribe({
      next: (event) => {
        if (event.type === 'start') {
          this.scanProgress.set({ scanned: 0, total: event.total });
          this.scanCapped.set(event.capped);
          if (event.total === 0) {
            this.error.set('No restaurants found for this zip code.');
          }
        } else if (event.type === 'restaurant') {
          this.items.update((list) => [...list, { restaurant: event.restaurant, scan: event.scan }]);
        } else if (event.type === 'progress') {
          this.scanProgress.set({ scanned: event.scanned, total: event.total });
        } else if (event.type === 'done') {
          this.loading.set(false);
          if (this.items().length === 0 && (this.scanProgress()?.total ?? 0) > 0) {
            this.error.set('No vegan dishes found in this area. Try a different zip code.');
          }
        }
      },
      error: () => {
        this.error.set('Streaming failed. Is the backend running?');
        this.loading.set(false);
      },
    });
  }
}
