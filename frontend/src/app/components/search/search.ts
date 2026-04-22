import { Component, OnDestroy, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { Restaurant, RestaurantService, ScanResult } from '../../services/restaurant';
import { RestaurantCard } from '../restaurant-card/restaurant-card';

type Mode = 'on-demand' | 'auto-scan';
const MODE_STORAGE_KEY = 'sprout-scout-mode';

interface ListItem {
  restaurant: Restaurant;
  scan?: ScanResult;
}

@Component({
  selector: 'app-search',
  imports: [FormsModule, RestaurantCard],
  templateUrl: './search.html',
  styleUrl: './search.scss',
})
export class Search implements OnDestroy {
  zipCode = '';
  mode = signal<Mode>(this.loadMode());
  items = signal<ListItem[]>([]);
  loading = signal(false);
  error = signal('');

  scanProgress = signal<{ scanned: number; total: number } | null>(null);
  scanCapped = signal(false);
  scanDone = signal(false);

  private streamSub?: Subscription;

  constructor(private restaurantService: RestaurantService) {}

  ngOnDestroy(): void {
    this.streamSub?.unsubscribe();
  }

  toggleMode() {
    const next: Mode = this.mode() === 'auto-scan' ? 'on-demand' : 'auto-scan';
    this.mode.set(next);
    try {
      localStorage.setItem(MODE_STORAGE_KEY, next);
    } catch {}
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
    this.scanDone.set(false);
    this.streamSub?.unsubscribe();

    if (this.mode() === 'auto-scan') {
      this.runAutoScan();
    } else {
      this.runOnDemand();
    }
  }

  private runOnDemand() {
    this.loading.set(true);
    this.restaurantService.getRestaurants(this.zipCode).subscribe({
      next: (res) => {
        this.items.set(res.restaurants.map((r) => ({ restaurant: r })));
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

  private runAutoScan() {
    this.loading.set(true);
    this.streamSub = this.restaurantService.scanStream(this.zipCode).subscribe({
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
          this.scanDone.set(true);
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

  private loadMode(): Mode {
    try {
      const v = localStorage.getItem(MODE_STORAGE_KEY);
      if (v === 'auto-scan' || v === 'on-demand') return v;
    } catch {}
    return 'on-demand';
  }
}
