import { Component } from '@angular/core';
import { Search } from './components/search/search';

@Component({
  selector: 'app-root',
  imports: [Search],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {}
