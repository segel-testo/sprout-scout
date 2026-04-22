import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Restaurant {
  id: string;
  name: string;
  address: string;
  website: string;
  phone: string;
  osm_diet_vegan?: string | null;
  osm_type?: string;
}

export interface VeganDish {
  name: string;
  confidence: number;
  matched_keywords: string[];
  source: string;
}

export interface FallbackLink {
  label: string;
  url: string;
}

export interface DeliveryLink {
  platform: string;
  url: string;
  label: string;
}

export interface ScanResult {
  restaurant_id: string;
  dishes: VeganDish[];
  no_menu?: boolean;
  fallback_links?: FallbackLink[];
  osm_diet_vegan?: string | null;
  delivery_link?: DeliveryLink | null;
}

export type ScanEvent =
  | { type: 'start'; total: number; total_available: number; capped: boolean }
  | { type: 'restaurant'; restaurant: Restaurant; scan: ScanResult }
  | { type: 'progress'; scanned: number; total: number }
  | { type: 'error'; restaurant_id: string; reason: string }
  | { type: 'done'; scanned: number; total: number };

@Injectable({ providedIn: 'root' })
export class RestaurantService {
  private apiUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) {}

  getRestaurants(zipCode: string): Observable<{ restaurants: Restaurant[] }> {
    return this.http.get<{ restaurants: Restaurant[] }>(
      `${this.apiUrl}/restaurants?zip_code=${zipCode}&country=AT`
    );
  }

  getVeganDishes(restaurant: Restaurant): Observable<ScanResult> {
    const params = new URLSearchParams({
      website: restaurant.website || '',
      name: restaurant.name || '',
      address: restaurant.address || '',
      osm_type: restaurant.osm_type || 'node',
    });
    if (restaurant.osm_diet_vegan) {
      params.set('osm_diet_vegan', restaurant.osm_diet_vegan);
    }
    return this.http.get<ScanResult>(
      `${this.apiUrl}/restaurants/${restaurant.id}/vegan?${params.toString()}`
    );
  }

  scanStream(zipCode: string): Observable<ScanEvent> {
    return new Observable<ScanEvent>((subscriber) => {
      const url = `${this.apiUrl}/restaurants/scan?zip_code=${zipCode}&country=AT`;
      const source = new EventSource(url);

      const forward = (type: ScanEvent['type']) => (ev: MessageEvent) => {
        try {
          const data = JSON.parse(ev.data);
          subscriber.next({ type, ...data } as ScanEvent);
          if (type === 'done') {
            source.close();
            subscriber.complete();
          }
        } catch (e) {
          subscriber.error(e);
        }
      };

      source.addEventListener('start', forward('start') as EventListener);
      source.addEventListener('restaurant', forward('restaurant') as EventListener);
      source.addEventListener('progress', forward('progress') as EventListener);
      source.addEventListener('error', forward('error') as EventListener);
      source.addEventListener('done', forward('done') as EventListener);

      source.onerror = () => {
        if (source.readyState === EventSource.CLOSED) {
          subscriber.complete();
        }
      };

      return () => source.close();
    });
  }
}
