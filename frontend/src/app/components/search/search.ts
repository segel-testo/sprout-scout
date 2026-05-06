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

export const RADIUS_OPTIONS: { value: number; label: string }[] = [
  { value: 500, label: '500 m' },
  { value: 1000, label: '1 km' },
  { value: 2000, label: '2 km' },
];

type Mode = 'zip' | 'radius';

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
  radiusOptions = RADIUS_OPTIONS;

  mode = signal<Mode>('zip');
  radius = signal<number>(500);
  coords = signal<{ lat: number; lon: number } | null>(null);
  geoStatus = signal<'idle' | 'locating' | 'ready' | 'denied' | 'unavailable'>('idle');

  items = signal<ListItem[]>([]);
  loading = signal(false);
  error = signal('');
  lastScanWasEmpty = signal(false);

  scanProgress = signal<{ scanned: number; total: number } | null>(null);
  scanCapped = signal(false);

  private streamSub?: Subscription;

  constructor(private restaurantService: RestaurantService) {}

  ngOnDestroy(): void {
    this.streamSub?.unsubscribe();
  }

  setMode(next: Mode) {
    if (this.mode() === next) return;
    this.mode.set(next);
    this.error.set('');
    this.lastScanWasEmpty.set(false);
  }

  private getFreshCoords(): Promise<{ lat: number; lon: number }> {
    return new Promise((resolve, reject) => {
      if (!('geolocation' in navigator)) {
        reject({ code: -1, message: 'unsupported' });
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        (err) => reject(err),
        { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
      );
    });
  }

  setRadius(value: number) {
    this.radius.set(value);
  }

  search() {
    if (this.mode() === 'zip') {
      this.searchByZip();
    } else {
      this.searchByRadius();
    }
  }

  private searchByZip() {
    if (!this.zipCode.match(/^\d{4}$/)) {
      this.error.set('Please enter a valid 4-digit Austrian zip code.');
      return;
    }
    this.startStream(this.restaurantService.scanStream(this.zipCode, this.selectedAmenity));
  }

  private async searchByRadius() {
    this.error.set('');
    this.geoStatus.set('locating');
    try {
      const c = await this.getFreshCoords();
      this.coords.set(c);
      this.geoStatus.set('ready');
      this.startStream(
        this.restaurantService.scanStreamByRadius(c.lat, c.lon, this.radius(), this.selectedAmenity),
      );
    } catch (err: any) {
      const denied = err?.code === 1;
      const unsupported = err?.code === -1;
      this.geoStatus.set(denied ? 'denied' : 'unavailable');
      this.coords.set(null);
      this.mode.set('zip');
      this.error.set(
        unsupported
          ? 'Your browser does not support geolocation. Switched back to zip search.'
          : denied
          ? 'Location access denied. Switched back to zip search.'
          : 'Could not determine your location. Switched back to zip search.',
      );
    }
  }

  private startStream(stream$: ReturnType<RestaurantService['scanStream']>) {
    this.error.set('');
    this.items.set([]);
    this.scanProgress.set(null);
    this.scanCapped.set(false);
    this.lastScanWasEmpty.set(false);
    this.streamSub?.unsubscribe();

    this.loading.set(true);
    this.streamSub = stream$.subscribe({
      next: (event) => {
        if (event.type === 'start') {
          this.scanProgress.set({ scanned: 0, total: event.total });
          this.scanCapped.set(event.capped);
          if (event.total === 0) {
            this.error.set(
              this.mode() === 'radius'
                ? 'No restaurants found within this radius.'
                : 'No restaurants found for this zip code.',
            );
          }
        } else if (event.type === 'restaurant') {
          this.items.update((list) => [...list, { restaurant: event.restaurant, scan: event.scan }]);
        } else if (event.type === 'progress') {
          this.scanProgress.set({ scanned: event.scanned, total: event.total });
        } else if (event.type === 'done') {
          this.loading.set(false);
          if (this.items().length === 0 && (this.scanProgress()?.total ?? 0) > 0) {
            this.error.set(
              this.mode() === 'radius'
                ? 'No vegan dishes found in this area.'
                : 'No vegan dishes found in this area. Try a different zip code.',
            );
            this.lastScanWasEmpty.set(true);
          }
        }
      },
      error: () => {
        this.error.set('Streaming failed. Is the backend running?');
        this.loading.set(false);
      },
    });
  }

  tryLargerRadius() {
    const next = this.radius() === 500 ? 1000 : 2000;
    this.radius.set(next);
    this.searchByRadius();
  }

  get suggestedNextRadiusLabel(): string | null {
    if (this.mode() !== 'radius') return null;
    if (this.radius() === 500) return '1 km';
    if (this.radius() === 1000) return '2 km';
    return null;
  }
}
