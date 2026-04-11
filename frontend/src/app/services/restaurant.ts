import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Restaurant {
  id: string;
  name: string;
  address: string;
  website: string;
  phone: string;
}

export interface VeganDish {
  name: string;
  confidence: number;
  matched_keywords: string[];
  source: string;
}

export interface VeganResult {
  restaurant_id: string;
  dishes: VeganDish[];
}

@Injectable({ providedIn: 'root' })
export class RestaurantService {
  private apiUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) {}

  getRestaurants(zipCode: string): Observable<{ restaurants: Restaurant[] }> {
    return this.http.get<{ restaurants: Restaurant[] }>(
      `${this.apiUrl}/restaurants?zip_code=${zipCode}&country=AT`
    );
  }

  getVeganDishes(restaurantId: string, website: string): Observable<VeganResult> {
    return this.http.get<VeganResult>(
      `${this.apiUrl}/restaurants/${restaurantId}/vegan?website=${encodeURIComponent(website)}`
    );
  }
}
